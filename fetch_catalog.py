#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
fetch_catalog.py - Nintendo Switch 2 全タイトルカタログ取得

Nintendo検索API (search.nintendo.jp/nintendo_soft/search.json) を使い、
Switch 2 (opt_hard=05_BEE) の全タイトル情報を取得して
data/catalog_switch2.json に保存する。

実行方法:
  python3 fetch_catalog.py

実行頻度の推奨:
  週1回（日曜 03:00）。価格更新（毎日 02:00）と被らないようにずらす。

  launchd プロパティリスト例（参考）:
  ~/Library/LaunchAgents/com.idaatsushi.gamesale.catalog.plist
  StartCalendarInterval: Weekday=0 Hour=3 Minute=0
  ProgramArguments: ["/usr/bin/python3", "/Users/idaatsushi/Desktop/ゲームセールサイト/gamesale/fetch_catalog.py"]

API について:
  - 認証不要・無料
  - opt_hard=05_BEE で Switch 2 のみ
  - opt_hard=1_HAC  で Switch（参考: 26,925件）
  - レスポンスにセール情報 (sprice/ssitu/ssdate/sedate) も含まれる
"""
from __future__ import annotations

import json
import sys
import time
from datetime import datetime
from pathlib import Path

import requests

# ============================================================
# 設定
# ============================================================
ROOT = Path(__file__).resolve().parent
OUT_FILE = ROOT / "data" / "catalog_switch2.json"

API_URL = "https://search.nintendo.jp/nintendo_soft/search.json"
HARD_CODE = "05_BEE"  # Switch 2

PAGE_SIZE = 100         # 1ページあたりの件数（API最大は要検証、100で安全側）
SLEEP_SEC = 0.5         # ページ間のスリープ（マナー対応）
TIMEOUT = 20            # リクエストタイムアウト
MAX_PAGES = 50          # 暴走防止上限（1,040件想定 → 11ページ程度で収まる）

# User-Agent に連絡先を含める（マナー＋トラブル時の対話可能性）
HEADERS = {
    "User-Agent": "gamesale-catalog/1.0 (+https://atsushi-ida.github.io/gamesale/)",
    "Accept-Language": "ja-JP,ja;q=0.9",
    "Accept": "application/json,text/plain,*/*",
}

# 保存する項目（API レスポンスのキーをそのまま使用）
# ※ 不要そうな内部キーを除外しつつ、後で使えそうなものは残す方針
KEEP_KEYS = [
    # 基本情報
    "id", "title", "titlek", "yomi",
    "nsuid", "icode", "cnsuid",
    "maker", "genre", "cero",
    "url",
    # 発売日・価格
    "pdate",                         # 発売日
    "sodate",                        # 配信開始日
    "sdate",                         # ?
    "vcsdate",                       # ?
    "pprice",                        # パッケージ定価
    "dprice",                        # DL版定価
    # セール情報（重要！）
    "sprice",                        # セール価格
    "ssitu",                         # セール状況
    "ssdate", "sedate",              # セール期間
    "ssdate2", "sedate2",            # 2回目セール（ある場合）
    # その他
    "hard",                          # ハード種別
    "sform",                         # 販売形式（パッケージ/DL）
    "iurl",                          # サムネイル画像URL
    "sicon",                         # アイコン
    "amiibo",                        # amiibo対応
    "n3ds",                          # 3DS互換等
    "right",                         # 権利表記
    "cdp",                           # ?
    "text",                          # 説明文
]


# ============================================================
# データ取得
# ============================================================
def fetch_page(page: int) -> dict:
    """1ページ取得"""
    params = {
        "limit": PAGE_SIZE,
        "page": page,
        "opt_hard": HARD_CODE,
    }
    r = requests.get(API_URL, params=params, headers=HEADERS, timeout=TIMEOUT)
    r.raise_for_status()
    return r.json()


def fetch_all() -> list[dict]:
    """全ページ取得"""
    all_items: list[dict] = []
    total: int | None = None

    for page in range(1, MAX_PAGES + 1):
        try:
            data = fetch_page(page)
        except requests.RequestException as e:
            print(f"  ⚠ ページ {page} で通信エラー: {e}")
            print(f"  3秒待って1回だけリトライ...")
            time.sleep(3)
            try:
                data = fetch_page(page)
            except requests.RequestException as e2:
                print(f"  ❌ リトライ失敗: {e2}")
                print(f"  ここまで取得した {len(all_items)} 件で打ち切ります")
                break

        result = data.get("result", {})
        items = result.get("items", [])
        if total is None:
            total = result.get("total", 0)
            print(f"  📊 API total = {total:,} 件")

        if not items:
            print(f"  ✓ ページ {page}: 空 → 取得完了")
            break

        all_items.extend(items)
        print(f"  ✓ ページ {page}: +{len(items)} 件 (累計 {len(all_items):,} / {total:,})")

        # 全件取得済みなら終了
        if len(all_items) >= total:
            break

        time.sleep(SLEEP_SEC)
    else:
        print(f"  ⚠ MAX_PAGES={MAX_PAGES} に到達。それ以上は打ち切り。")

    return all_items


# ============================================================
# 整形
# ============================================================
def slim(item: dict) -> dict:
    """KEEP_KEYS だけ残し、欠落キーは無視"""
    return {k: item[k] for k in KEEP_KEYS if k in item}


def add_image_candidates(item: dict) -> dict:
    """
    画像候補を統合。後で楽天画像と差し替える判断ができるよう、
    Nintendo の iurl と、サイズ別バリエーションを保存。
    """
    iurl = item.get("iurl") or ""
    candidates: list[dict] = []
    if iurl:
        candidates.append({"source": "nintendo", "url": iurl})

    # 楽天画像は別途取得するため、ここではプレースホルダ
    # （fetch_rakuten_images.py を後日作成して埋める想定）
    item["image_candidates"] = candidates
    return item


# ============================================================
# 統計
# ============================================================
def summarize(items: list[dict]) -> dict:
    """カタログ全体のざっくり統計"""
    today = datetime.now().strftime("%Y-%m-%d")

    on_sale = [i for i in items if i.get("sprice")]
    unreleased = [i for i in items if i.get("pdate") and i["pdate"] > today]
    has_image = [i for i in items if i.get("iurl")]
    has_dl = [i for i in items if i.get("dprice")]
    has_pkg = [i for i in items if i.get("pprice")]

    # 発売日範囲
    dates = [i["pdate"] for i in items if i.get("pdate")]
    earliest = min(dates) if dates else "-"
    latest = max(dates) if dates else "-"

    # メーカー TOP 5
    maker_count: dict[str, int] = {}
    for i in items:
        m = i.get("maker") or "(不明)"
        maker_count[m] = maker_count.get(m, 0) + 1
    top_makers = sorted(maker_count.items(), key=lambda x: -x[1])[:5]

    return {
        "total": len(items),
        "on_sale": len(on_sale),
        "unreleased": len(unreleased),
        "has_image": len(has_image),
        "has_dl_price": len(has_dl),
        "has_pkg_price": len(has_pkg),
        "date_range": f"{earliest} 〜 {latest}",
        "top_makers": top_makers,
    }


# ============================================================
# メイン
# ============================================================
def main() -> int:
    print("=" * 60)
    print(f"📦 Nintendo Switch 2 カタログ取得 ({datetime.now():%Y-%m-%d %H:%M:%S})")
    print("=" * 60)
    print()

    # 取得
    print("【取得開始】")
    raw_items = fetch_all()
    print(f"  → 生データ {len(raw_items):,} 件取得完了")
    print()

    if not raw_items:
        print("❌ 取得結果が0件です。API仕様変更の可能性があります。")
        return 1

    # 整形
    print("【整形】")
    items = [add_image_candidates(slim(i)) for i in raw_items]
    print(f"  → {len(items):,} 件を整形完了")
    print()

    # 統計
    print("【取得結果サマリ】")
    s = summarize(items)
    print(f"  総タイトル数      : {s['total']:>5,} 件")
    print(f"  セール中          : {s['on_sale']:>5,} 件")
    print(f"  未発売            : {s['unreleased']:>5,} 件")
    print(f"  画像URLあり       : {s['has_image']:>5,} 件")
    print(f"  DL版価格あり      : {s['has_dl_price']:>5,} 件")
    print(f"  パッケージ価格あり : {s['has_pkg_price']:>5,} 件")
    print(f"  発売日レンジ      : {s['date_range']}")
    print(f"  メーカー TOP 5    :")
    for maker, count in s["top_makers"]:
        print(f"    - {maker:30s} {count:>4} 件")
    print()

    # 保存
    print("【保存】")
    OUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "fetched_at": datetime.now().isoformat(timespec="seconds"),
        "source": API_URL,
        "hard_code": HARD_CODE,
        "platform": "Nintendo Switch 2",
        "summary": s,
        "items": items,
    }
    OUT_FILE.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    size_kb = OUT_FILE.stat().st_size / 1024
    print(f"  💾 {OUT_FILE.relative_to(ROOT)} ({size_kb:,.1f} KB)")
    print()

    # サンプル表示（先頭3件）
    print("【サンプル（先頭3件）】")
    for i, item in enumerate(items[:3], 1):
        title = item.get("title", "?")[:40]
        maker = item.get("maker", "?")
        pdate = item.get("pdate", "?")
        nsuid = item.get("nsuid", "?")
        print(f"  {i}. {title}")
        print(f"     メーカー: {maker} / 発売日: {pdate} / nsuid: {nsuid}")
    print()

    print("✅ 完了！")
    print()
    print("=" * 60)
    print("次のステップ:")
    print("  1. data/catalog_switch2.json を確認")
    print("  2. セール中タイトルを既存サイトに反映する設計を検討")
    print("  3. 楽天画像取得スクリプト (fetch_rakuten_images.py) の追加")
    print("=" * 60)
    return 0


if __name__ == "__main__":
    sys.exit(main())
