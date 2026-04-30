filepath = "/Users/idaatsushi/Desktop/ゲームセールサイト/gamesale/fetch_prices.py"
with open(filepath, "r", encoding="utf-8") as f:
    src = f.read()

# 順序ループ内でfile_size_gbを引き継ぐ処理を追加
old = '    entry, results = game_results[game_id]\n        for plat, data in results:'
new = '''    entry, results = game_results[game_id]
        # 既存のfile_size_gbを引き継ぐ
        prev = all_prices.get("games", {}).get(game_id, {})
        if prev.get("file_size_gb") is not None:
            entry["file_size_gb"] = prev["file_size_gb"]
        for plat, data in results:'''
src = src.replace(old, new)

# データ保存の直前にPlaywright取得ループを追加
old = 'print("\\n【データ保存】")'
new = '''# 容量未取得のeショップタイトルをPlaywrightで取得
print("\\n【容量取得】")
for game_id, entry in all_prices.get("games", {}).items():
    if entry.get("file_size_gb") is None and entry.get("nsuid"):
        print(f"  🔍 {entry['title']} ...", end=" ", flush=True)
        size = fetch_file_size(entry["nsuid"])
        if size:
            entry["file_size_gb"] = size
cat << 'EOF' > ~/Desktop/ゲームセールサイト/gamesale/patch_filesize2.py
filepath = "/Users/idaatsushi/Desktop/ゲームセールサイト/gamesale/fetch_prices.py"
with open(filepath, "r", encoding="utf-8") as f:
    src = f.read()

# 順序ループ内でfile_size_gbを引き継ぐ処理を追加
old = '    entry, results = game_results[game_id]\n        for plat, data in results:'
new = '''    entry, results = game_results[game_id]
        # 既存のfile_size_gbを引き継ぐ
        prev = all_prices.get("games", {}).get(game_id, {})
        if prev.get("file_size_gb") is not None:
            entry["file_size_gb"] = prev["file_size_gb"]
        for plat, data in results:'''
src = src.replace(old, new)

# データ保存の直前にPlaywright取得ループを追加
old = 'print("\\n【データ保存】")'
new = '''# 容量未取得のeショップタイトルをPlaywrightで取得
print("\\n【容量取得】")
for game_id, entry in all_prices.get("games", {}).items():
    if entry.get("file_size_gb") is None and entry.get("nsuid"):
        print(f"  🔍 {entry['title']} ...", end=" ", flush=True)
        size = fetch_file_size(entry["nsuid"])
        if size:
            entry["file_size_gb"] = size
            print(f"{size}GB ✅")
        else:
            print("取得不可")

print("\\n【データ保存】")'''
src = src.replace(old, new)

with open(filepath, "w", encoding="utf-8") as f:
    f.write(src)
print("✅ パッチ2完了")
