"""
ゲーセル - 価格データ取得スクリプト v6
オクトパストラベラー2 nsuid追加
"""

import json
import time
import datetime
import requests
from pathlib import Path

DATA_DIR = Path("data")
PRICES_FILE = DATA_DIR / "prices.json"
HISTORY_FILE = DATA_DIR / "history.json"
REQUEST_INTERVAL = 1.5

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept-Language": "ja-JP,ja;q=0.9",
}

GAMES = [
    {"id": "persona5_royal", "title": "ペルソナ5 ザ・ロイヤル", "maker": "アトラス", "nsuid": "70010000042356", "steam_id": "1687950", "is_switch2": False},
    {"id": "mhrise_sunbreak", "title": "モンスターハンターライズ：サンブレイク セット", "maker": "カプコン", "nsuid": "70070000013655", "steam_id": "1446780", "is_switch2": False},
    {"id": "dq11s", "title": "ドラゴンクエストXI S 過ぎ去りし時を求めて S", "maker": "スクウェア・エニックス", "nsuid": "70070000006461", "steam_id": "860510", "is_switch2": False},
    {"id": "xenoblade3", "title": "ゼノブレイド3", "maker": "任天堂", "nsuid": "70010000053335", "steam_id": None, "is_switch2": False},
    {"id": "biohazard_village", "title": "バイオハザード ヴィレッジ", "maker": "カプコン", "nsuid": None, "steam_id": "1196590", "is_switch2": False},
    {"id": "octopath2", "title": "オクトパストラベラー2", "maker": "スクウェア・エニックス", "nsuid": "70010000058127", "steam_id": "1993360", "is_switch2": False},
    {"id": "guilty_gear_strive", "title": "GUILTY GEAR -STRIVE-", "maker": "アークシステムワークス", "nsuid": None, "steam_id": "1384160", "is_switch2": False},
    {"id": "lies_of_p", "title": "Lies of P", "maker": "NEOWIZ", "nsuid": None, "steam_id": "1627720", "is_switch2": False},
    {"id": "sekiro", "title": "SEKIRO: SHADOWS DIE TWICE", "maker": "フロムソフトウェア", "nsuid": None, "steam_id": "814380", "is_switch2": False},
    {"id": "elden_ring", "title": "ELDEN RING", "maker": "フロムソフトウェア", "nsuid": None, "steam_id": "1245620", "is_switch2": False},
]


def today_str():
    return datetime.date.today().isoformat()

def load_json(filepath):
    if filepath.exists():
        with open(filepath, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

def save_json(filepath, data):
    filepath.parent.mkdir(parents=True, exist_ok=True)
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"  ✓ 保存: {filepath}")

def update_history(history, game_id, platform, price_data):
    if not price_data or not price_data.get("on_sale"):
        return history
    key = f"{game_id}_{platform}"
    if key not in history:
        history[key] = {"game_id": game_id, "platform": platform, "all_time_low": None, "all_time_low_date": None, "records": []}
    current = price_data.get("sale_price")
    if not current:
        return history
    entry = history[key]
    today = today_str()
    if entry["all_time_low"] is None or current < entry["all_time_low"]:
        entry["all_time_low"] = current
        entry["all_time_low_date"] = today
        print(f"    🏆 過去最安値更新！ {game_id} [{platform}]: ¥{current}")
    existing = [r["date"] for r in entry["records"]]
    if today not in existing:
        entry["records"].append({"date": today, "sale_price": current, "regular_price": price_data.get("regular_price"), "discount_pct": price_data.get("discount_pct")})
        entry["records"] = sorted(entry["records"], key=lambda x: x["date"])[-365:]
    return history

def fetch_eshop_price(nsuid):
    url = "https://api.ec.nintendo.com/v1/price"
    params = {"country": "JP", "lang": "ja", "ids": nsuid}
    try:
        resp = requests.get(url, params=params, headers=HEADERS, timeout=15)
        resp.raise_for_status()
        data = resp.json()
        prices = data.get("prices", [])
        if not prices:
            return None
        price_info = prices[0]
        status = price_info.get("sales_status", "")
        if status == "not_found":
            return {"status": "not_found", "on_sale": False}
        regular = price_info.get("regular_price", {})
        discount = price_info.get("discount_price", {})
        reg_val = int(regular.get("raw_value", 0))
        if discount and status == "onsale":
            disc_val = int(discount.get("raw_value", 0))
            disc_pct = round((1 - disc_val / reg_val) * 100) if reg_val > 0 else 0
            end_date = discount.get("end_datetime", "")
            return {"status": "on_sale", "on_sale": True, "regular_price": reg_val, "sale_price": disc_val, "discount_pct": disc_pct, "sale_end": end_date[:10] if end_date else None, "currency": "JPY", "fetched_at": today_str()}
        else:
            return {"status": "not_on_sale", "on_sale": False, "regular_price": reg_val, "sale_price": None, "discount_pct": 0, "currency": "JPY", "fetched_at": today_str()}
    except Exception as e:
        print(f"    ⚠ eショップエラー: {e}")
        return None

def fetch_steam_price(steam_id):
    url = "https://store.steampowered.com/api/appdetails"
    params = {"appids": steam_id, "cc": "jp", "l": "japanese"}
    try:
        resp = requests.get(url, params=params, headers=HEADERS, timeout=15)
        resp.raise_for_status()
        data = resp.json()
        app_data = data.get(str(steam_id), {})
        if not app_data.get("success"):
            return None
        game_data = app_data.get("data", {})
        price_overview = game_data.get("price_overview")
        if not price_overview:
            return None
        regular_price = price_overview.get("initial", 0) // 100
        sale_price = price_overview.get("final", 0) // 100
        discount_pct = price_overview.get("discount_percent", 0)
        return {"status": "on_sale" if discount_pct > 0 else "not_on_sale", "on_sale": discount_pct > 0, "regular_price": regular_price, "sale_price": sale_price if discount_pct > 0 else None, "discount_pct": discount_pct, "currency": "JPY", "fetched_at": today_str()}
    except Exception as e:
        print(f"    ⚠ Steamエラー: {e}")
        return None

def main():
    print("=" * 50)
    print("ゲーセル 価格取得スクリプト v6")
    print(f"実行日時: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 50)

    history = load_json(HISTORY_FILE)
    today = today_str()
    all_prices = {"last_updated": today, "games": {}}

    print("\n【価格取得開始】")
    eshop_on_sale = 0
    steam_on_sale = 0

    for game in GAMES:
        game_id = game["id"]
        print(f"\n  📦 {game['title']}")
        game_entry = {"id": game_id, "title": game["title"], "maker": game["maker"], "is_switch2": game.get("is_switch2", False), "nsuid": game.get("nsuid"), "steam_id": game.get("steam_id"), "prices": {}}

        if game.get("nsuid"):
            eshop_data = fetch_eshop_price(game["nsuid"])
            if eshop_data:
                game_entry["prices"]["eshop"] = eshop_data
                history = update_history(history, game_id, "eshop", eshop_data)
                if eshop_data.get("on_sale"):
                    eshop_on_sale += 1
                    print(f"    🎮 eショップ: ¥{eshop_data['sale_price']} (-{eshop_data['discount_pct']}%) 🔥")
                else:
                    print(f"    🎮 eショップ: ¥{eshop_data.get('regular_price','?')} 通常価格")
            time.sleep(REQUEST_INTERVAL)

        if game.get("steam_id"):
            steam_data = fetch_steam_price(game["steam_id"])
            if steam_data:
                game_entry["prices"]["steam"] = steam_data
                history = update_history(history, game_id, "steam", steam_data)
                if steam_data.get("on_sale"):
                    steam_on_sale += 1
                    print(f"    🖥️ Steam: ¥{steam_data['sale_price']} (-{steam_data['discount_pct']}%) 🔥")
                else:
                    print(f"    🖥️ Steam: ¥{steam_data.get('regular_price','?')} 通常価格")
            time.sleep(REQUEST_INTERVAL)

        for platform in ["eshop", "steam"]:
            key = f"{game_id}_{platform}"
            if key in history and platform in game_entry["prices"]:
                game_entry["prices"][platform]["all_time_low"] = history[key].get("all_time_low")
                game_entry["prices"][platform]["all_time_low_date"] = history[key].get("all_time_low_date")

        all_prices["games"][game_id] = game_entry

    print("\n【データ保存】")
    save_json(PRICES_FILE, all_prices)
    save_json(HISTORY_FILE, history)

    print("\n" + "=" * 50)
    print("✅ 完了！")
    print(f"  eショップ セール中: {eshop_on_sale}件")
    print(f"  Steam セール中: {steam_on_sale}件")
    for gid, gdata in all_prices["games"].items():
        for plat, pdata in gdata.get("prices", {}).items():
            if pdata.get("on_sale"):
                print(f"  🔥 {gdata['title']} [{plat}] ¥{pdata.get('sale_price')} (-{pdata.get('discount_pct')}%)")
    print("=" * 50)

if __name__ == "__main__":
    main()
