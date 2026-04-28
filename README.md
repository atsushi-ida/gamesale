# ゲーセル - セットアップ手順

## 全体の流れ

```
① GitHubアカウント作成（無料）
② リポジトリ作成
③ ファイルをアップロード
④ GitHub Pages有効化
⑤ GitHub Actionsが毎日自動でデータ取得
⑥ サイトが自動更新される
```

---

## Step 1: ファイル構成

```
your-repo/
├── index.html              ← フロントエンド（サイト本体）
├── fetch_prices.py         ← 価格取得スクリプト
├── .github/
│   └── workflows/
│       └── fetch-prices.yml  ← 自動実行設定
└── data/
    ├── prices.json         ← 現在の価格データ（自動生成）
    └── history.json        ← 価格履歴（自動蓄積）
```

---

## Step 2: GitHubリポジトリ作成

1. https://github.com にアクセス
2. 右上「+」→「New repository」
3. Repository name: `gamesale`（任意）
4. Public を選択（GitHub Pagesを使うため）
5. 「Create repository」

---

## Step 3: ファイルをアップロード

GitHubのWebページから直接アップロードできます：
1. リポジトリページで「uploading an existing file」をクリック
2. ファイルをドラッグ＆ドロップ
3. 「Commit changes」

または Git が使える場合：
```bash
git clone https://github.com/あなたのID/gamesale.git
cd gamesale
# ファイルをコピーして...
git add .
git commit -m "初回アップロード"
git push
```

---

## Step 4: GitHub Pages 有効化

1. リポジトリの「Settings」タブ
2. 左メニュー「Pages」
3. Source: 「Deploy from a branch」
4. Branch: `main` / `/ (root)`
5. 「Save」

数分後に `https://あなたのID.github.io/gamesale/` でアクセス可能に。

---

## Step 5: Actions の権限設定

GitHub Actionsがデータをコミットできるように設定：
1. リポジトリの「Settings」→「Actions」→「General」
2. 「Workflow permissions」で「Read and write permissions」を選択
3. 「Save」

---

## Step 6: 監視ゲームの追加方法

`fetch_prices.py` の `GAMES` リストにゲームを追加します：

```python
{
    "id": "game_unique_id",          # 半角英数字・アンダーバーのみ
    "title": "ゲームタイトル（日本語OK）",
    "maker": "メーカー名",
    "nsuid": "70010000XXXXXXX",      # eショップID（下記参照）
    "steam_id": "XXXXXXX",           # Steam AppID（下記参照）
    "ps_concept_id": None,           # PS Store ID（調査中）
    "xbox_id": None,                 # Xbox ID（調査中）
},
```

### nsuid（eショップID）の調べ方
1. https://store-jp.nintendo.com でゲームページを開く
2. URLの末尾の数字が nsuid
   例: `.../70010000063875` → nsuid は `70010000063875`

### Steam AppID の調べ方
1. https://store.steampowered.com でゲームページを開く
2. URLの `app/` の後の数字が AppID
   例: `.../app/2050650/` → AppID は `2050650`

---

## 手動でデータ取得する場合

ローカルで実行する場合：

```bash
# 必要なライブラリのインストール
pip install requests

# 実行
python fetch_prices.py
```

---

## 収益化設定

### Google AdSense
1. https://www.google.com/adsense にアクセス
2. サイトURLを登録して審査申請
3. 審査通過後、index.html の広告枠コードを置き換え

### Amazon アソシエイト
1. https://affiliate.amazon.co.jp に登録
2. サイトURLを申請
3. 承認後、商品リンクを生成してindex.htmlに設置

### 楽天アフィリエイト
1. https://affiliate.rakuten.co.jp に登録
2. サイトURLを申請
3. 承認後、商品リンクを生成

---

## トラブルシューティング

### データが取得できない
- eショップAPIのURLが変わった可能性あり
- `fetch_prices.py` の URLを確認・更新する

### GitHub Actionsが動かない
- Settingsの「Actions permissions」を確認
- 「Workflow permissions」が「Read and write」になっているか確認

### サイトが表示されない
- GitHub Pagesの設定を確認（Step 4）
- `index.html` がリポジトリのルートにあるか確認
