#!/bin/bash
cd ~/Desktop/ゲームセールサイト/gamesale
git pull --no-rebase
python3 fetch_prices.py
git add data/
git diff --staged --quiet || git commit -m "価格データ更新: $(date '+%Y-%m-%d')"
git push
