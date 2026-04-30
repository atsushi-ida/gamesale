import re

filepath = "/Users/idaatsushi/Desktop/ゲームセールサイト/gamesale/fetch_prices.py"
with open(filepath, "r", encoding="utf-8") as f:
    src = f.read()

# 1. fetch_file_size関数をfetch_game関数の直前に追加
func = '''
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
            for line in text.split('\\n'):
                if '容量' in line:
                    m = re2.search(r'([\\d.]+)\\s*GB', line)
                    if m:
                        return float(m.group(1))
    except Exception as e:
        print(f"  ⚠ 容量取得エラー {nsuid}: {e}")
    return None

'''

src = src.replace("    def fetch_game(game):", func + "    def fetch_game(game):")

# 2. entryにfile_size_gbを追加
old_entry = '"prices": {}\n    }'
new_entry = '"prices": {}, "file_size_gb": None\n    }'
src = src.replace(old_entry, new_entry)

with open(filepath, "w", encoding="utf-8") as f:
    f.write(src)
print("✅ パッチ完了")
