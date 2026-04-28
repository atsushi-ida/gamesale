"""
ゲーセル - 価格データ取得スクリプト
=====================================
取得対象:
  - Nintendo eショップ（日本）
  - Steam（日本円）
  - PlayStation Store（日本）
  - Xbox / Microsoft Store（日本）

実行方法:
  python fetch_prices.py

出力:
  data/prices.json     - 現在の価格データ
  data/history.json    - 過去の価格履歴（蓄積型）

GitHub Actionsで毎日自動実行することを想定。
"""

import json
import time
import datetime
import os
import requests
from pathlib import Path

# ========== 設定 ==========
DATA_DIR = Path("data")
PRICES_FILE = DATA_DIR / "prices.json"
HISTORY_FILE = DATA_DIR / "history.json"

# リクエスト間隔（サーバー負荷対策・マナーとして必ず守る）
REQUEST_INTERVAL = 1.5  # 秒

HEADERS = {
    "User-Agent": "GamesalePriceTracker/1.0 (price comparison site; contact: your@email.com)"
}

# ========== 監視対象ゲームリスト ==========
# nsuid: 任天堂eショップの商品ID（store-jp.nintendo.comのURLから取得）
# steam_id: SteamのアプリID（store.steampowered.comのURLから取得）
# ps_id: PS StoreのコンセプトID（store.playstation.comのURLから取得）
# xbox_id: XboxのProduct ID

GAMES = [
    {
        "id": "biohazard_re4",
        "title": "バイオハザード RE:4 ゴールドエディション",
        "maker": "カプコン",
        "nsuid": "70010000063875",      # eショップID
        "steam_id": "2050650",          # Steam AppID
        "ps_concept_id": "10007553",    # PS Store ID（要確認）
        "xbox_id": None,                # Xbox ID（要調査）
    },
    {
        "id": "persona5_royal",
        "title": "ペルソナ5 ザ・ロイヤル",
        "maker": "アトラス",
        "nsuid": "70010000043826",
        "steam_id": "1687950",
        "ps_concept_id": "10000490",
        "xbox_id": None,
    },
    {
        "id": "mhrise_sunbreak",
        "title": "モンスターハンターライズ：サンブレイク",
        "maker": "カプコン",
        "nsuid": "70010000049822",
        "steam_id": "1446780",
        "ps_concept_id": "10007456",
        "xbox_id": None,
    },
    {
        "id": "dq11s",
        "title": "ドラゴンクエストXI S 過ぎ去りし時を求めて S",
        "maker": "スクウェア・エニックス",
        "nsuid": "70010000014130",
        "steam_id": "860510",
        "ps_concept_id": None,
        "xbox_id": None,
    },
    {
        "id": "xenoblade3",
        "title": "ゼノブレイド3",
        "maker": "任天堂",
        "nsuid": "70010000046551",
        "steam_id": None,              # Steam版なし
        "ps_concept_id": None,         # PS版なし
        "xbox_id": None,
    },
]


# ========== ユーティリティ ==========

def safe_get(url, params=None, timeout=10):
    """安全なHTTP GETリクエスト（エラーハンドリング付き）"""
    try:
        resp = requests.get(url, params=params, headers=HEADERS, timeout=timeout)
        resp.raise_for_status()
        return resp.json()
    except requests.exceptions.HTTPError as e:
        print(f"    ⚠ HTTP Error: {e}")
    except requests.exceptions.Timeout:
        print(f"    ⚠ タイムアウト: {url}")
    except requests.exceptions.ConnectionError:
        print(f"    ⚠ 接続エラー: {url}")
    except json.JSONDecodeError:
        print(f"    ⚠ JSONパースエラー: {url}")
    except Exception as e:
        print(f"    ⚠ 予期しないエラー: {e}")
    return None


def today_str():
    return datetime.date.today().isoformat()


# ========== eショップ（任天堂日本） ==========

def fetch_eshop_price(nsuid):
    """
    任天堂の非公式エンドポイントで価格取得
    ※公式APIではないため、変更・廃止の可能性あり
    ※レート制限に注意（連続リクエスト禁止）
    """
    url = "https://api.ec.nintendo.com/v1/price"
    params = {
        "country": "JP",
        "lang": "ja",
        "ids": nsuid,
    }
    data = safe_get(url, params=params)
    if not data:
        return None

    try:
        price_info = data["prices"][0]
        sales_status = price_info.get("sales_status", "")

        # 販売中でない場合はスキップ
        if sales_status != "onsale":
            return {"status": sales_status, "on_sale": False}

        regular = price_info.get("regular_price", {})
        discount = price_info.get("discount_price", {})

        regular_price = int(float(regular.get("raw_value", 0)))

        if discount:
            sale_price = int(float(discount.get("raw_value", 0)))
            end_date = discount.get("end_datetime", "")
            discount_pct = round((1 - sale_price / regular_price) * 100) if regular_price > 0 else 0
            return {
                "status": "on_sale",
                "on_sale": True,
                "regular_price": regular_price,
                "sale_price": sale_price,
                "discount_pct": discount_pct,
                "sale_end": end_date[:10] if end_date else None,
                "currency": "JPY",
                "fetched_at": today_str(),
            }
        else:
            return {
                "status": "not_on_sale",
                "on_sale": False,
                "regular_price": regular_price,
                "sale_price": None,
                "discount_pct": 0,
                "currency": "JPY",
                "fetched_at": today_str(),
            }
    except (KeyError, IndexError, TypeError) as e:
        print(f"    ⚠ eショップデータ解析エラー: {e}")
        return None


def fetch_eshop_all_sales():
    """
    現在セール中の全タイトルを取得
    1回のAPIコールで最大200件取得可能
    """
    print("  eショップ セール一覧を取得中...")
    all_sales = []
    offset = 0
    count = 200

    while True:
        url = "https://ec.nintendo.com/api/JP/ja/search/sales"
        params = {"count": count, "offset": offset}
        data = safe_get(url, params=params)

        if not data:
            break

        contents = data.get("contents", [])
        if not contents:
            break

        all_sales.extend(contents)
        total = data.get("total", 0)
        offset += count

        print(f"    取得中: {len(all_sales)}/{total}件")

        if offset >= total:
            break

        time.sleep(REQUEST_INTERVAL)

    print(f"  ✓ eショップ セール: {len(all_sales)}件取得")
    return all_sales


# ========== Steam ==========

def fetch_steam_price(app_id):
    """
    Steam Store APIで日本円価格を取得
    ※Valveの公式エンドポイントだが商用利用は利用規約上グレー
    ※広く使われており実害なしで黙認されている
    """
    url = "https://store.steampowered.com/api/appdetails"
    params = {
        "appids": app_id,
        "cc": "jp",       # 日本
        "l": "japanese",
    }
    data = safe_get(url, params=params)
    if not data:
        return None

    try:
        app_data = data.get(str(app_id), {})
        if not app_data.get("success"):
            return None

        game_data = app_data.get("data", {})
        price_overview = game_data.get("price_overview")

        if not price_overview:
            # 無料ゲームの場合
            if game_data.get("is_free"):
                return {"status": "free", "on_sale": False, "regular_price": 0}
            return None

        regular_price = price_overview.get("initial", 0) // 100  # 銭→円
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
    except (KeyError, TypeError) as e:
        print(f"    ⚠ Steamデータ解析エラー: {e}")
        return None


# ========== PlayStation Store ==========

def fetch_ps_price(concept_id):
    """
    PlayStation Store 非公式エンドポイントで価格取得
    ※公式APIではないため変更の可能性あり
    ※psdeals.net等が同様の手法を使用
    """
    # PS StoreのGraphQL APIエンドポイント（非公式）
    url = "https://store.playstation.com/store/api/chihiro/00_09_000/container/JP/ja/19"
    # 注意: このエンドポイントは変更される可能性が高い
    # 実装時に最新のエンドポイントを確認すること
    # 現時点では安定したエンドポイントが確認できないため
    # 実装はスケルトンとして提供

    print(f"    ⚠ PS Store APIは現在調査中です（concept_id: {concept_id}）")
    print(f"    ℹ psdeals.net等の手法を参考に実装してください")
    return None


# ========== Xbox / Microsoft Store ==========

def fetch_xbox_price(product_id):
    """
    Microsoft Store 非公式エンドポイントで価格取得
    ※公式APIではないため変更の可能性あり
    """
    if not product_id:
        return None

    url = "https://displaycatalog.mp.microsoft.com/v7.0/products"
    params = {
        "productIds": product_id,
        "market": "JP",
        "languages": "ja-jp",
        "MS-CV": "DGU1mcuYo0WMMp",
    }
    data = safe_get(url, params=params)
    if not data:
        return None

    try:
        products = data.get("Products", [])
        if not products:
            return None

        product = products[0]
        displays = product.get("DisplaySkuAvailabilities", [])
        if not displays:
            return None

        # 最初のSKUの価格を取得
        sku = displays[0]
        availabilities = sku.get("Availabilities", [])
        if not availabilities:
            return None

        price_info = availabilities[0].get("OrderManagementData", {}).get("Price", {})
        list_price = price_info.get("ListPrice", 0)
        msrp = price_info.get("MSRP", list_price)

        discount_pct = round((1 - list_price / msrp) * 100) if msrp > 0 else 0

        return {
            "status": "on_sale" if discount_pct > 0 else "not_on_sale",
            "on_sale": discount_pct > 0,
            "regular_price": int(msrp),
            "sale_price": int(list_price) if discount_pct > 0 else None,
            "discount_pct": discount_pct,
            "currency": "JPY",
            "fetched_at": today_str(),
        }
    except (KeyError, IndexError, TypeError) as e:
        print(f"    ⚠ Xboxデータ解析エラー: {e}")
        return None


# ========== 履歴の保存・読み込み ==========

def load_json(filepath):
    """JSONファイルを読み込む（存在しない場合は空を返す）"""
    if filepath.exists():
        with open(filepath, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


def save_json(filepath, data):
    """JSONファイルに保存"""
    filepath.parent.mkdir(parents=True, exist_ok=True)
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"  ✓ 保存: {filepath}")


def update_history(history, game_id, platform, price_data):
    """
    価格履歴を更新する
    過去最安値の追跡・蓄積を行う
    """
    if not price_data or not price_data.get("on_sale"):
        return history

    key = f"{game_id}_{platform}"
    if key not in history:
        history[key] = {
            "game_id": game_id,
            "platform": platform,
            "all_time_low": None,
            "all_time_low_date": None,
            "records": []
        }

    current_sale_price = price_data.get("sale_price")
    if not current_sale_price:
        return history

    entry = history[key]
    today = today_str()

    # 過去最安値の更新
    if (entry["all_time_low"] is None or
            current_sale_price < entry["all_time_low"]):
        entry["all_time_low"] = current_sale_price
        entry["all_time_low_date"] = today
        print(f"    🏆 過去最安値更新！ {game_id} on {platform}: ¥{current_sale_price}")

    # 今日のレコードを追加（重複チェック）
    existing_dates = [r["date"] for r in entry["records"]]
    if today not in existing_dates:
        entry["records"].append({
            "date": today,
            "sale_price": current_sale_price,
            "regular_price": price_data.get("regular_price"),
            "discount_pct": price_data.get("discount_pct"),
        })
        # 直近365日分のみ保持
        entry["records"] = sorted(entry["records"], key=lambda x: x["date"])[-365:]

    return history


# ========== メイン処理 ==========

def main():
    print("=" * 50)
    print("ゲーセル 価格取得スクリプト")
    print(f"実行日時: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 50)

    # 既存データの読み込み
    all_prices = load_json(PRICES_FILE)
    history = load_json(HISTORY_FILE)

    today = today_str()
    all_prices["last_updated"] = today
    all_prices["games"] = all_prices.get("games", {})

    # ========== eショップ セール一覧取得 ==========
    print("\n【1】eショップ セール一覧取得")
    eshop_sales = fetch_eshop_all_sales()
    # セール中のnsuidを辞書化（高速検索用）
    eshop_sale_map = {}
    for item in eshop_sales:
        nsuid = str(item.get("id", ""))
        if nsuid:
            eshop_sale_map[nsuid] = item
    all_prices["eshop_all_sales"] = {
        "count": len(eshop_sales),
        "updated": today,
    }
    time.sleep(REQUEST_INTERVAL)

    # ========== ゲームごとの価格取得 ==========
    print("\n【2】個別ゲーム価格取得")

    for game in GAMES:
        game_id = game["id"]
        print(f"\n  📦 {game['title']}")

        if game_id not in all_prices["games"]:
            all_prices["games"][game_id] = {
                "title": game["title"],
                "maker": game["maker"],
                "prices": {}
            }

        game_entry = all_prices["games"][game_id]

        # --- eショップ ---
        if game.get("nsuid"):
            print(f"    🎮 eショップ取得中...")
            eshop_data = fetch_eshop_price(game["nsuid"])
            if eshop_data:
                game_entry["prices"]["eshop"] = eshop_data
                history = update_history(history, game_id, "eshop", eshop_data)
                status = "セール中 🔥" if eshop_data.get("on_sale") else "通常価格"
                price = eshop_data.get("sale_price") or eshop_data.get("regular_price")
                print(f"    ✓ eショップ: ¥{price} ({status})")
            time.sleep(REQUEST_INTERVAL)

        # --- Steam ---
        if game.get("steam_id"):
            print(f"    🖥️ Steam取得中...")
            steam_data = fetch_steam_price(game["steam_id"])
            if steam_data:
                game_entry["prices"]["steam"] = steam_data
                history = update_history(history, game_id, "steam", steam_data)
                status = "セール中 🔥" if steam_data.get("on_sale") else "通常価格"
                price = steam_data.get("sale_price") or steam_data.get("regular_price")
                print(f"    ✓ Steam: ¥{price} ({status})")
            time.sleep(REQUEST_INTERVAL)

        # --- PlayStation ---
        if game.get("ps_concept_id"):
            print(f"    🎯 PS Store取得中...")
            ps_data = fetch_ps_price(game["ps_concept_id"])
            if ps_data:
                game_entry["prices"]["ps"] = ps_data
                history = update_history(history, game_id, "ps", ps_data)
            time.sleep(REQUEST_INTERVAL)

        # --- Xbox ---
        if game.get("xbox_id"):
            print(f"    🟩 Xbox取得中...")
            xbox_data = fetch_xbox_price(game["xbox_id"])
            if xbox_data:
                game_entry["prices"]["xbox"] = xbox_data
                history = update_history(history, game_id, "xbox", xbox_data)
            time.sleep(REQUEST_INTERVAL)

    # ========== 過去最安値を価格データに反映 ==========
    print("\n【3】過去最安値データを反映")
    for game in GAMES:
        game_id = game["id"]
        for platform in ["eshop", "steam", "ps", "xbox"]:
            key = f"{game_id}_{platform}"
            if key in history:
                h = history[key]
                if game_id in all_prices["games"]:
                    prices = all_prices["games"][game_id]["prices"]
                    if platform in prices:
                        prices[platform]["all_time_low"] = h.get("all_time_low")
                        prices[platform]["all_time_low_date"] = h.get("all_time_low_date")

    # ========== 保存 ==========
    print("\n【4】データ保存")
    save_json(PRICES_FILE, all_prices)
    save_json(HISTORY_FILE, history)

    # ========== サマリー ==========
    print("\n" + "=" * 50)
    print("✅ 完了！")
    on_sale_count = 0
    for game_id, game_data in all_prices["games"].items():
        for platform, pdata in game_data.get("prices", {}).items():
            if pdata.get("on_sale"):
                on_sale_count += 1
                title = game_data["title"]
                price = pdata.get("sale_price")
                disc = pdata.get("discount_pct")
                print(f"  🔥 {title} [{platform}] ¥{price} (-{disc}%)")

    print(f"\n  セール中: {on_sale_count}件")
    print(f"  データ更新: {today}")
    print("=" * 50)


if __name__ == "__main__":
    main()
