"""
ゲーセル - 価格データ取得スクリプト（修正版）
eショップのセール一覧を全件取得する方式に変更
"""

import json
import time
import datetime
import requests
from pathlib import Path

DATA_DIR = Path("data")
PRICES_FILE = DATA_DIR / "prices.json"
HISTORY_FILE = DATA_DIR / "history.json"
REQUEST_INTERVAL = 2.0

HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; GamesaleBot/1.0)",
    "Accept": "application/json",
    "Accept-Language": "ja-JP,ja;q=0.9",
}

STEAM_GAMES = [
    {"id": "persona5_royal", "title": "ペルソナ5 ザ・ロイヤル", "maker": "アトラス", "steam_id": "1687950"},
    {"id": "mhrise_sunbreak", "title": "モンスターハンターライズ：サンブレイク", "maker": "カプコン", "steam_id": "1446780"},
    {"id": "dq11s", "title": "ドラゴンクエストXI S", "maker": "スクウェア・エニックス", "steam_id": "860510"},
    {"id": "biohazard_re4", "title": "バイオハザード RE:4", "maker": "カプコン", "steam_id": "2050650"},
    {"id": "biohazard_village", "title": "バイオハザード ヴィレッジ", "maker": "カプコン", "steam_id": "1196590"},
    {"id": "octopath2", "title": "オクトパストラベラー2", "maker": "スクウェア・エニックス", "steam_id": "1993360"},
    {"id": "guilty_gear_strive", "title": "GUILTY GEAR -STRIVE-", "maker": "アークシステムワークス", "steam_id": "1384160"},
]


def today_str():
    return datetime.date.today().isoformat()


def safe_get(url, params=None, timeout=15):
    try:
        resp = requests.get(url, params=params, headers=HEADERS, timeout=timeout)
        resp.raise_for_status()
        return resp.json()
    except Exception as e:
        print(f"    ⚠ エラー: {e}")
        return None


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


def fetch_eshop_all_sales():
    print("\n【1】eショップ セール一覧取得...")
    all_sales = []
    offset = 0
    count = 200

    while True:
        url = "https://ec.nintendo.com/api/JP/ja/search/sales"
        params = {"count": count, "offset": offset}
        data = safe_get(url, params=params)
        if not data:
            url2 = "https://ec.nintendo.com/JP/ja/search/sales"
            data = safe_get(url2, params=params)
        if not data:
            print("  ⚠ eショップAPIにアクセスできませんでした")
            break

        contents = data.get("contents", [])
        if not contents:
            break

        for item in contents:
            try:
                price_info = item.get("price", {})
                regular = price_info.get("regularPrice", {})
                discount = price_info.get("discountPrice", {})
                if not discount:
                    continue
                reg_val = int(float(regular.get("rawValue", 0)))
                disc_val = int(float(discount.get("rawValue", 0)))
                disc_pct = round((1 - disc_val / reg_val) * 100) if reg_val > 0 else 0
                end_date = discount.get("endDatetime", "")
                platforms = item.get("platforms", [])
                is_switch2 = any("switch2" in str(p).lower() or "NS2" in str(p) for p in platforms)
                sale_entry = {
                    "nsuid": str(item.get("id", "")),
                    "title": item.get("title", ""),
                    "maker": item.get("makerName", ""),
                    "genre": item.get("genre", ""),
                    "platforms": platforms,
                    "is_switch2": is_switch2,
                    "regular_price": reg_val,
                    "sale_price": disc_val,
                    "discount_pct": disc_pct,
                    "sale_end": end_date[:10] if end_date else None,
                    "on_sale": True,
                    "fetched_at": today_str(),
                }
                all_sales.append(sale_entry)
            except Exception:
                continue

        total = data.get("total", 0)
        offset += count
        print(f"  取得中: {len(all_sales)}/{total}件")
        if offset >= total or not contents:
            break
        time.sleep(REQUEST_INTERVAL)

    print(f"  ✓ eショップ セール: {len(all_sales)}件")
    return all_sales


def fetch_steam_price(steam_id):
    url = "https://store.steampowered.com/api/appdetails"
    params = {"appids": steam_id, "cc": "jp", "l": "japanese"}
    data = safe_get(url, params=params)
    if not data:
        return None
    try:
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
        return {
            "status": "on_sale" if discount_pct > 0 else "not_on_sale",
            "on_sale": discount_pct > 0,
            "regular_price": regular_price,
            "sale_price": sale_price if discount_pct > 0 else None,
            "discount_pct": discount_pct,
            "currency": "JPY",
            "fetched_at": today_str(),
        }
    except Exception as e:
        print(f"    ⚠ Steamエラー: {e}")
        return None


def main():
    print("=" * 50)
    print("ゲーセル 価格取得スクリプト")
    print(f"実行日時: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 50)

    history = load_json(HISTORY_FILE)
    today = today_str()

    all_prices = {
        "last_updated": today,
        "eshop_sales": [],
        "steam_games": {},
    }

    eshop_sales = fetch_eshop_all_sales()
    all_prices["eshop_sales"] = eshop_sales
    all_prices["eshop_sale_count"] = len(eshop_sales)

    for item in eshop_sales:
        nsuid = item.get("nsuid", "")
        if nsuid:
            history = update_history(history, f"eshop_{nsuid}", "eshop", {
                "on_sale": True,
                "sale_price": item.get("sale_price"),
                "regular_price": item.get("regular_price"),
                "discount_pct": item.get("discount_pct"),
            })

    time.sleep(REQUEST_INTERVAL)

    print("\n【2】Steam価格取得...")
    for game in STEAM_GAMES:
        print(f"  🖥️ {game['title']}...")
        steam_data = fetch_steam_price(game["steam_id"])
        if steam_data:
            all_prices["steam_games"][game["id"]] = {
                "id": game["id"],
                "title": game["title"],
                "maker": game["maker"],
                "steam_id": game["steam_id"],
                "prices": {"steam": steam_data}
            }
            history = update_history(history, game["id"], "steam", steam_data)
            status = f"¥{steam_data.get('sale_price')} (-{steam_data.get('discount_pct')}%) 🔥" if steam_data.get("on_sale") else f"¥{steam_data.get('regular_price')} 通常"
            print(f"    ✓ {status}")
        time.sleep(REQUEST_INTERVAL)

    print("\n【3】データ保存")
    save_json(PRICES_FILE, all_prices)
    save_json(HISTORY_FILE, history)

    print("\n" + "=" * 50)
    print("✅ 完了！")
    print(f"  eショップ セール中: {len(eshop_sales)}件")
    steam_on_sale = [g for g in all_prices["steam_games"].values() if g.get("prices", {}).get("steam", {}).get("on_sale")]
    print(f"  Steam セール中: {len(steam_on_sale)}件")
    for g in steam_on_sale:
        sd = g["prices"]["steam"]
        print(f"  🔥 {g['title']} ¥{sd.get('sale_price')} (-{sd.get('discount_pct')}%)")
    print("=" * 50)


if __name__ == "__main__":
    main()
