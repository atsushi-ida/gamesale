"""
ゲーセル - 価格データ取得スクリプト v7
並列処理対応・Switch2タイトル追加
"""

import json
import time
import datetime
import requests
from bs4 import BeautifulSoup
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed

DATA_DIR = Path("data")
PRICES_FILE = DATA_DIR / "prices.json"
HISTORY_FILE = DATA_DIR / "history.json"
PERIPHERALS_FILE = DATA_DIR / "peripherals.json"
REQUEST_INTERVAL = 1.5

# 周辺機器リスト（直接URLを指定、msrp=メーカー希望小売価格）
PERIPHERALS = [
    {"id": "sw2_pro",    "name": "Switch2 プロコントローラー", "msrp": 9980,  "url": "https://item.rakuten.co.jp/book/18210484/"},
    {"id": "sw2_body",   "name": "Nintendo Switch2 本体",      "msrp": 49980, "url": "https://item.rakuten.co.jp/book/18210481/"},
    {"id": "sw_pro",     "name": "Switch プロコントローラー",   "msrp": 7678,  "url": "https://item.rakuten.co.jp/book/14647228/"},
    {"id": "ds_white",   "name": "DualSense コントローラー 白", "msrp": 9480,  "url": "https://books.rakuten.co.jp/rb/18440638/"},
    {"id": "ds_black",   "name": "DualSense コントローラー 黒", "msrp": 9480,  "url": "https://books.rakuten.co.jp/rb/18440639/"},
    {"id": "samsung512", "name": "Samsung microSDXpress 512GB", "msrp": 19980, "url": "https://item.rakuten.co.jp/itgm/4560441099989/"},
    {"id": "sandisk256", "name": "SanDisk microSDExpress 256GB","msrp": 8980,  "url": "https://books.rakuten.co.jp/rb/18210486/"},
]

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
    # Switch2専用タイトル
    {"id": "mariokart_world", "title": "マリオカート ワールド", "maker": "任天堂", "nsuid": "70010000092842", "steam_id": None, "is_switch2": True},
    {"id": "donkey_kong_bananza", "title": "ドンキーコング バナンザ", "maker": "任天堂", "nsuid": "70010000096306", "steam_id": None, "is_switch2": True},
    {"id": "poco_a_pokemon", "title": "ぽこ あ ポケモン", "maker": "任天堂", "nsuid": "70010000107420", "steam_id": None, "is_switch2": True},
    {"id": "deltarune", "title": "DELTARUNE", "maker": "tobyfox", "nsuid": "70010000096639", "steam_id": None, "is_switch2": True},
    {"id": "pokemon_za", "title": "Pokémon LEGENDS Z-A", "maker": "ゲームフリーク", "nsuid": "70010000094233", "steam_id": None, "is_switch2": False},
    {"id": "split_fiction", "title": "スプリット・フィクション", "maker": "EA", "nsuid": "70010000096944", "steam_id": "2001120", "is_switch2": True},
    {"id": "sw2_himitsu", "title": "Nintendo Switch 2 のひみつ展", "maker": "任天堂", "nsuid": "70010000096305", "steam_id": None, "is_switch2": True},
    {"id": "duskbloods", "title": "The Duskbloods", "maker": "フロムソフトウェア", "nsuid": "70010000096715", "steam_id": None, "is_switch2": True},
    {"id": "splatoon_raiders", "title": "スプラトゥーン レイダース", "maker": "任天堂", "nsuid": "70010000122823", "steam_id": None, "is_switch2": True},
    {"id": "fantasy_life_i_sw2", "title": "ファンタジーライフ i SW2 Edition", "maker": "レベルファイブ", "nsuid": "70010000098486", "steam_id": None, "is_switch2": True},
    {"id": "pokemon_za_sw2", "title": "Pokemon LEGENDS Z-A Nintendo Switch 2 Edition", "maker": "ゲームフリーク", "nsuid": "70010000099190", "steam_id": None, "is_switch2": True},
    {"id": "kirby_air_riders", "title": "カービィのエアライダー", "maker": "任天堂", "nsuid": "70010000103774", "steam_id": None, "is_switch2": True},
    {"id": "mario_party_jamboree", "title": "スーパーマリオパーティ ジャンボリー Nintendo Switch 2 Edition", "maker": "任天堂", "nsuid": "70010000013977", "steam_id": None, "is_switch2": True},
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
        # セール終了 → sale_start をリセット
        key = f"{game_id}_{platform}"
        if key in history:
            history[key].pop("current_sale_start", None)
        return history
    key = f"{game_id}_{platform}"
    if key not in history:
        history[key] = {"game_id": game_id, "platform": platform, "all_time_low": None, "all_time_low_date": None, "records": []}
    current = price_data.get("sale_price")
    if not current:
        return history
    entry = history[key]
    today = today_str()
    # セール開始日の追跡
    if "current_sale_start" not in entry:
        entry["current_sale_start"] = today
    if entry["all_time_low"] is None or current < entry["all_time_low"]:
        entry["all_time_low"] = current
        entry["all_time_low_date"] = today
        print(f"    🏆 過去最安値更新！ {game_id} [{platform}]: ¥{current}")
    existing = [r["date"] for r in entry["records"]]
    if today not in existing:
        entry["records"].append({"date": today, "sale_price": current, "regular_price": price_data.get("regular_price"), "discount_pct": price_data.get("discount_pct")})
        entry["records"] = sorted(entry["records"], key=lambda x: x["date"])[-365:]
    return history

import re as _re

def fetch_rakuten_price(url):
    """楽天商品ページから価格をスクレイピング（item.rakuten / books.rakuten 両対応）"""
    try:
        resp = requests.get(url, headers=HEADERS, timeout=15)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")
        is_books = "books.rakuten.co.jp" in url

        if is_books:
            # books.rakuten: class="price"の最初の要素が実売価格
            # class="strikethru"は参考小売価格なので除外
            for el in soup.find_all(class_="price"):
                text = el.get_text(strip=True)
                m = _re.search(r"([\d,]{4,})", text)
                if m:
                    price = int(m.group(1).replace(",", ""))
                    if 1000 <= price <= 300000:
                        return price
            return None

        # item.rakuten.co.jp: JSON-LDが信頼できる
        for s in soup.find_all("script", type="application/ld+json"):
            try:
                d = json.loads(s.string or "")
                offers = d.get("offers", {})
                if isinstance(offers, list):
                    offers = offers[0]
                p = offers.get("price") or offers.get("lowPrice")
                if p:
                    price = int(float(str(p).replace(",", "")))
                    if 1000 <= price <= 300000:
                        return price
            except Exception:
                pass

        # item.rakuten.co.jp 専用セレクタ
        for sel in [
            "span.price--OKm9j",
            ".price--OKm9j",
            "[class*='price__main']",
            "[class*='ItemPrice']",
            ".item-price",
        ]:
            el = soup.select_one(sel)
            if el:
                text = el.get_text(strip=True)
                m = _re.search(r"[\d,]{4,}", text)
                if m:
                    price = int(m.group(0).replace(",", ""))
                    if 1000 <= price <= 300000:
                        return price

        return None
    except Exception as e:
        print(f"    ⚠ 楽天スクレイプエラー ({url}): {e}")
        return None

def fetch_and_save_peripherals(existing_peripherals):
    """周辺機器の価格を取得してperipherals.jsonに保存"""
    print("\n【周辺機器価格取得】")
    prev_items = {i["id"]: i for i in existing_peripherals.get("items", [])}
    items_out = []
    for p in PERIPHERALS:
        print(f"  🔍 {p['name']}...", end=" ", flush=True)
        price = fetch_rakuten_price(p["url"])
        if price:
            print(f"¥{price:,}")
        else:
            price = prev_items.get(p["id"], {}).get("price")
            print(f"取得失敗（前回値: ¥{price:,}）" if price else "取得失敗")
        items_out.append({"id": p["id"], "price": price, "msrp": p.get("msrp")})
        time.sleep(REQUEST_INTERVAL)
    result = {"last_updated": today_str(), "items": items_out}
    save_json(PERIPHERALS_FILE, result)
    return result

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
            sale_name = discount.get("promotion_name") or regular.get("promotion_name") or None
            return {"status": "on_sale", "on_sale": True, "regular_price": reg_val, "sale_price": disc_val, "discount_pct": disc_pct, "sale_end": end_date[:10] if end_date else None, "sale_name": sale_name, "currency": "JPY", "fetched_at": today_str()}
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
        sale_name = None
        if discount_pct > 0:
            # Steam APIのdiscount_reasonがあれば使う、なければ"-% OFF"で表記
            sale_name = price_overview.get("discount_reason") or f"Steam セール -{discount_pct}%"
        return {"status": "on_sale" if discount_pct > 0 else "not_on_sale", "on_sale": discount_pct > 0, "regular_price": regular_price, "sale_price": sale_price if discount_pct > 0 else None, "discount_pct": discount_pct, "sale_name": sale_name, "currency": "JPY", "fetched_at": today_str()}
    except Exception as e:
        print(f"    ⚠ Steamエラー: {e}")
        return None

def fetch_geo_campaign_slug():
    """ゲオのセール・キャンペーンページから現在のスラグを自動検出"""
    import re as re2
    try:
        resp = requests.get("https://geo-online.co.jp/store_info/sale_campaign/", headers=HEADERS, timeout=15)
        soup = BeautifulSoup(resp.text, "html.parser")
        for a in soup.find_all("a", href=re2.compile(r"/store_info/sale_campaign/\w+/flier")):
            m = re2.search(r"/store_info/sale_campaign/(\w+)/flier", a["href"])
            if m:
                return m.group(1)
        # フォールバック: セールリンクから推測
        for a in soup.find_all("a", href=re2.compile(r"/store_info/sale_campaign/\w+")):
            m = re2.search(r"/store_info/sale_campaign/(\w+)(?:/|$)", a["href"])
            slug = m.group(1) if m else None
            if slug and slug not in ["", "sale_campaign"]:
                return slug
    except Exception as e:
        print(f"  ⚠ スラグ検出エラー: {e}")
    return None

def normalize_title(title):
    """タイトル正規化（全角→半角、記号除去）"""
    import unicodedata, re as re2
    title = unicodedata.normalize("NFKC", title)
    title = re2.sub(r"【.*?】|\(.*?\)（.*?）|　", " ", title)
    title = re2.sub(r"\s+", " ", title).strip().lower()
    return title

def match_geo_to_games(geo_items, games_list):
    """ゲオのゲームタイトルをGAMESリストに照合"""
    from difflib import SequenceMatcher
    matched = {}  # game_id -> {price, geo_title, category}
    for geo in geo_items:
        geo_norm = normalize_title(geo["title"])
        best_score = 0
        best_id = None
        for game in games_list:
            game_norm = normalize_title(game["title"])
            score = SequenceMatcher(None, geo_norm, game_norm).ratio()
            if score > best_score:
                best_score = score
                best_id = game["id"]
        if best_score >= 0.6 and best_id:
            # 既存より安ければ更新
            if best_id not in matched or geo["price"] < matched[best_id]["price"]:
                matched[best_id] = {
                    "price": geo["price"],
                    "geo_title": geo["title"],
                    "category": geo.get("category", ""),
                    "match_score": round(best_score, 2)
                }
    return matched

def fetch_geo_list_page(url):
    """ゲオのリストページから全アイテムを取得"""
    import re as re2
    items = []
    try:
        resp = requests.get(url, headers=HEADERS, timeout=15)
        soup = BeautifulSoup(resp.text, "html.parser")
        # カテゴリ名取得
        cat_el = soup.select_one("h1, h2, .category-title")
        category = cat_el.get_text(strip=True) if cat_el else ""
        # 商品リスト取得
        for li in soup.select("li"):
            title_el = li.select_one("h2, h3, p")
            price_el = li.find(string=re2.compile(r"[\d,]+円"))
            if not title_el:
                continue
            title = re2.sub(r"【中古】|【.*?】", "", title_el.get_text(strip=True)).strip()
            if not title or len(title) < 3:
                continue
            price = None
            if price_el:
                m = re2.search(r"([\d,]+)円", price_el)
                if m:
                    price = int(m.group(1).replace(",", ""))
            if title and price and 100 <= price <= 50000:
                items.append({"title": title, "price": price, "category": category})
        time.sleep(REQUEST_INTERVAL)
    except Exception as e:
        print(f"  ⚠ リストページエラー ({url}): {e}")
    return items

def fetch_geo_prices():
    """ゲオのセール情報を取得してgeo_prices.jsonに保存"""
    print("\n【ゲオ中古価格取得】")
    slug = fetch_geo_campaign_slug()
    if not slug:
        print("  ⚠ キャンペーンスラグが検出できませんでした")
        return
    print(f"  キャンペーン: {slug}")

    flier_url = f"https://geo-online.co.jp/store_info/sale_campaign/{slug}/flier.html"
    all_items = []
    sale_end = None
    campaign_name = slug

    try:
        resp = requests.get(flier_url, headers=HEADERS, timeout=15)
        soup = BeautifulSoup(resp.text, "html.parser")

        # キャンペーン名・期間取得
        h1 = soup.select_one("h1")
        if h1:
            campaign_name = h1.get_text(strip=True)
        import re as re2
        title_text = soup.title.string if soup.title else ""
        m = re2.search(r"(\d+月\d+日)", title_text + campaign_name)
        if m:
            sale_end = m.group(1)

        # 「もっと見る」リンクからリストページURLを収集
        list_urls = []
        for a in soup.find_all("a", string=re2.compile(r"もっと見る")):
            href = a.get("href", "")
            if "list.html" in href:
                full_url = href if href.startswith("http") else "https://geo-online.co.jp" + href
                if full_url not in list_urls:
                    list_urls.append(full_url)

        # フライヤーページ上のアイテムも取得
        for section in soup.select("section, .section, ul"):
            for li in section.select("li"):
                title_el = li.select_one("h3, h4, p")
                price_el = li.find(string=re2.compile(r"[\d,]+円"))
                if not title_el:
                    continue
                title = re2.sub(r"【中古】|【.*?】", "", title_el.get_text(strip=True)).strip()
                if not title or len(title) < 3:
                    continue
                price = None
                if price_el:
                    pm = re2.search(r"([\d,]+)円", price_el)
                    if pm:
                        price = int(pm.group(1).replace(",", ""))
                if title and price and 100 <= price <= 50000:
                    # カテゴリを上位h3から推定
                    cat_el = section.find_previous(["h2", "h3"])
                    cat = cat_el.get_text(strip=True) if cat_el else ""
                    all_items.append({"title": title, "price": price, "category": cat})

        # リストページを取得
        for list_url in list_urls[:8]:
            print(f"  📋 {list_url.split('?')[-1]}...", end=" ", flush=True)
            items = fetch_geo_list_page(list_url)
            print(f"{len(items)}件")
            all_items.extend(items)

    except Exception as e:
        print(f"  ⚠ フライヤー取得エラー: {e}")
        return

    if not all_items:
        print("  ⚠ アイテムが取得できませんでした")
        return

    print(f"  取得合計: {len(all_items)}件")

    # GAMESリストと照合
    matched = match_geo_to_games(all_items, GAMES)
    print(f"  マッチ: {len(matched)}件")
    for gid, info in matched.items():
        print(f"    ✅ {gid} ← {info['geo_title']} ¥{info['price']:,} (スコア:{info['match_score']})")

    result = {
        "last_updated": today_str(),
        "campaign_name": campaign_name,
        "sale_end": sale_end,
        "slug": slug,
        "matched_games": matched,
        "all_items": all_items[:200]  # 最大200件保存
    }
    save_json(DATA_DIR / "geo_prices.json", result)



def update_file_sizes_in_html(all_prices):
    """prices.jsonのfile_size_gbをindex.htmlのFILE_SIZESに反映"""
    import re
    from pathlib import Path
    html_path = Path(__file__).parent / "index.html"
    if not html_path.exists():
        return
    lines = ["const FILE_SIZES = {\n"]
    for game_id, game in all_prices.get("games", {}).items():
        size = game.get("file_size_gb")
        if size is not None:
            label = f"{size} GB"
            lines.append(f"  {game_id}:{{ gb: {size}, label: \'{label}\' }},\n")
        else:
            lines.append(f"  {game_id}:{{ gb: null, label: \'未定\' }},\n")
    lines.append("};\n")
    new_block = "".join(lines)
    html = html_path.read_text(encoding="utf-8")
    html_new = re.sub(r'const FILE_SIZES = \{.*?\};', new_block, html, flags=re.DOTALL)
    if html_new != html:
        html_path.write_text(html_new, encoding="utf-8")
        print("  ✅ index.html FILE_SIZES更新完了")


def fetch_release_date(title):
    """Nintendo JP検索APIから発売日を取得"""
    try:
        import requests as req2
        url = 'https://search.nintendo.jp/nintendo_soft/search.json'
        r = req2.get(url, params={'q': title, 'limit': 1}, headers=HEADERS, timeout=10)
        data = r.json()
        if 'result' in data and 'items' in data['result'] and data['result']['items']:
            item = data['result']['items'][0]
            pdate = item.get('pdate')
            if pdate:
                return pdate[:10]  # YYYY-MM-DD形式
    except Exception as e:
        print(f"  ⚠ 発売日取得エラー {title}: {e}")
    return None

def fetch_file_size(nsuid):
    """PlaywrightでeショップからGB容量を取得（初回のみ）"""
    try:
        from playwright.sync_api import sync_playwright
        import re as re2
        url = f'https://store-jp.nintendo.com/list/software/{nsuid}.html'
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            page.goto(url, wait_until='domcontentloaded', timeout=30000)
            page.wait_for_timeout(5000)
            text = page.inner_text('body')
            browser.close()
            for line in text.split('\n'):
                m = re2.search(r'([\d.]+)\s*GB', line)
                if m:
                    return float(m.group(1))
    except Exception as e:
        print(f"  ⚠ 容量取得エラー {nsuid}: {e}")
    return None

def main():
    print("=" * 50)
    print("ゲーセル 価格取得スクリプト v7")
    print(f"実行日時: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 50)

    history = load_json(HISTORY_FILE)
    today = today_str()
    all_prices = {"last_updated": today, "games": {}}

    print("\n【価格取得開始（並列処理）】")


    def fetch_game(game):
        """1タイトル分の価格を取得して返す"""
        game_id = game["id"]
        entry = {
            "id": game_id, "title": game["title"], "maker": game["maker"],
            "is_switch2": game.get("is_switch2", False),
            "nsuid": game.get("nsuid"), "steam_id": game.get("steam_id"),
            "prices": {}
        }
        results = []
        if game.get("nsuid"):
            data = fetch_eshop_price(game["nsuid"])
            if data:
                entry["prices"]["eshop"] = data
                results.append(("eshop", data))
        if game.get("steam_id"):
            data = fetch_steam_price(game["steam_id"])
            if data:
                entry["prices"]["steam"] = data
                results.append(("steam", data))
        return game_id, entry, results

    # 最大5並列でゲーム価格を取得
    game_results = {}
    with ThreadPoolExecutor(max_workers=5) as executor:
        futures = {executor.submit(fetch_game, g): g for g in GAMES}
        for future in as_completed(futures):
            game_id, entry, results = future.result()
            game_results[game_id] = (entry, results)
            title = entry["title"]
            for plat, data in results:
                icon = "🎮" if plat == "eshop" else "🖥️"
                if data.get("on_sale"):
                    print(f"  🔥 {title} [{plat}] ¥{data.get('sale_price')} (-{data.get('discount_pct')}%)")
                else:
                    print(f"  📦 {title} [{plat}] ¥{data.get('regular_price','?')} 通常")

    eshop_on_sale = 0
    steam_on_sale = 0

    # 順序を保ってall_pricesに格納・history更新
    for game in GAMES:
        game_id = game["id"]
        if game_id not in game_results:
            continue
        entry, results = game_results[game_id]
        # 既存のfile_size_gbを引き継ぐ
        prev = all_prices.get("games", {}).get(game_id, {})
        if prev.get("file_size_gb") is not None:
            entry["file_size_gb"] = prev["file_size_gb"]
        for plat, data in results:
            history = update_history(history, game_id, plat, data)
            if data.get("on_sale"):
                if plat == "eshop": eshop_on_sale += 1
                else: steam_on_sale += 1
        for platform in ["eshop", "steam"]:
            key = f"{game_id}_{platform}"
            if key in history and platform in entry["prices"]:
                entry["prices"][platform]["all_time_low"] = history[key].get("all_time_low")
                entry["prices"][platform]["all_time_low_date"] = history[key].get("all_time_low_date")
                entry["prices"][platform]["sale_start"] = history[key].get("current_sale_start")
        all_prices["games"][game_id] = entry

        # 容量未取得のeショップタイトルをPlaywrightで取得

    # 容量未取得タイトルをPlaywrightで取得
    print("\n【容量取得】")
    for game_id, entry in all_prices.get("games", {}).items():
        if entry.get("file_size_gb") is None and entry.get("nsuid"):
            print(f"  🔍 {entry['title']} ...", end=" ", flush=True)
            size = fetch_file_size(entry["nsuid"])
            if size:
                entry["file_size_gb"] = size
                print(f"{size}GB ✅")
            else:
                print("取得不可")
    print("\n【データ保存】")
    save_json(PRICES_FILE, all_prices)
    save_json(HISTORY_FILE, history)
    # 発売日未取得タイトルを取得
    print("\n【発売日取得】")
    for game_id, entry in all_prices.get("games", {}).items():
        if entry.get("release_date") is None and entry.get("title"):
            print(f"  📅 {entry['title']} ...", end=" ", flush=True)
            date = fetch_release_date(entry["title"])
            if date:
                entry["release_date"] = date
                print(f"{date} ✅")
            else:
                print("取得不可")
    # index.htmlのFILE_SIZESを自動更新
    update_file_sizes_in_html(all_prices)

    # 周辺機器・ゲオは並列で同時取得
    print("\n【周辺機器・ゲオ 並列取得】")
    existing_peripherals = load_json(PERIPHERALS_FILE) if PERIPHERALS_FILE.exists() else {}
    with ThreadPoolExecutor(max_workers=2) as executor:
        f_peri = executor.submit(fetch_and_save_peripherals, existing_peripherals)
        f_geo  = executor.submit(fetch_geo_prices)
        f_peri.result()
        f_geo.result()

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
