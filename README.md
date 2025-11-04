# Reaction Finder

Slackワークスペース内で特定の絵文字リアクションが多く付けられている投稿を検索・抽出するCLIツールです。

## 特徴

- 🔍 ワークスペース全体から特定の絵文字リアクションを検索
- 📊 リアクション数でランキング表示
- 📅 日付範囲を指定して検索可能
- 💻 シンプルなCLIインターフェース
- 🚀 1回の実行で完結

## 使用例

チームメンバーへの感謝の投稿を探したり、人気の投稿を見つけるのに便利です：
```bash
# 直近30日間で :pray: リアクションが多い投稿を検索
python3 reaction_finder.py pray --days 30

# 2024年Q4の :thanks: リアクションTop5
python3 reaction_finder.py thanks --after 2024-10-01 --before 2024-12-31 -n 5
```

## インストール

### 1. リポジトリをクローン
```bash
git clone https://github.com/Dai1678/slack_reaction_finder.git
cd slack_reaction_finder
```

### 2. 依存関係をインストール
```bash
pip3 install slack-sdk
```

または
```bash
pip3 install -r requirements.txt
```

## セットアップ

### Slack Appの作成

1. [Slack API](https://api.slack.com/apps) にアクセス
2. 「Create New App」をクリック
3. 「From scratch」を選択
4. アプリ名とワークスペースを指定

### 必要なスコープの追加

「OAuth & Permissions」で以下のBot Token Scopesを追加：

- `channels:history` - パブリックチャンネルの履歴を読む
- `channels:read` - パブリックチャンネル情報を読む
- `groups:history` - プライベートチャンネルの履歴を読む
- `groups:read` - プライベートチャンネル情報を読む
- `im:history` - DMの履歴を読む
- `reactions:read` - リアクション情報を読む
- `search:read` - ワークスペース内を検索
- `users:read` - ユーザー情報を読む

### トークンの取得

1. 「Install to Workspace」をクリック
2. 権限を承認
3. 表示される「Bot User OAuth Token」（`xoxb-`で始まる）をコピー

### 環境変数の設定（推奨）
```bash
# ~/.bashrc または ~/.zshrc に追加
export SLACK_REACTION_FINDER_TOKEN="xoxb-your-token-here"
```

または、実行時に `-t` オプションで指定することもできます。

## 使い方

### 基本的な使い方
```bash
python3 reaction_finder.py <絵文字名> [オプション]
```

### オプション

| オプション | 短縮形 | 説明 | デフォルト |
|----------|--------|------|-----------|
| `--top` | `-n` | 表示する上位件数 | 3 |
| `--token` | `-t` | Slack Bot Token | 環境変数または設定値 |
| `--after` | - | この日付以降（YYYY-MM-DD） | なし |
| `--before` | - | この日付以前（YYYY-MM-DD） | なし |
| `--on` | - | この日付（YYYY-MM-DD） | なし |
| `--days` | - | 直近N日間 | なし |
| `--help` | `-h` | ヘルプを表示 | - |

### 実行例

#### 基本的な検索
```bash
# :pray: リアクションが多い投稿Top3
python3 reaction_finder.py pray

# :thanks: リアクションが多い投稿Top10
python3 reaction_finder.py thanks -n 10
```

#### 日付指定
```bash
# 直近30日間
python3 reaction_finder.py pray --days 30

# 2024年1月1日以降
python3 reaction_finder.py thanks --after 2024-01-01

# 2024年12月31日以前
python3 reaction_finder.py tada --before 2024-12-31

# 2024年Q1（1-3月）
python3 reaction_finder.py pray --after 2024-01-01 --before 2024-03-31

# 2024年10月1日
python3 reaction_finder.py thanks --on 2024-10-01

# 2024年12月31日から遡って90日間
python3 reaction_finder.py thanks --days 90 --before 2024-12-31
```

#### トークン指定
```bash
# コマンドラインで直接指定
python3 reaction_finder.py pray -t xoxb-your-token-here

# 環境変数から読み込み
python3 reaction_finder.py pray -t $SLACK_TOKEN
```

### 出力例
```
:pray: リアクションが多い投稿を検索中...
期間指定: after:2024-10-01 before:2024-12-31

検索結果: 45 件の投稿が見つかりました
上位100件を取得して分析します...

処理中: 45/45

================================================================================
:pray: リアクションが多い投稿 Top 3
================================================================================

【第1位】 28 個のリアクション
日時: 2024年11月15日 14:23:45
チャンネル: #general
投稿者: 山田太郎
内容: プロジェクトの成功に向けて尽力してくれた皆さん、本当にありがとうございました！...
リンク: https://your-workspace.slack.com/archives/C1234567/p1234567890123456

【第2位】 22 個のリアクション
日時: 2024年10月28日 09:15:22
チャンネル: #team-updates
投稿者: 佐藤花子
内容: リリース対応お疲れ様でした。深夜まで対応してくれた開発チームに感謝です...
リンク: https://your-workspace.slack.com/archives/C7891011/p7891011121314151

【第3位】 18 個のリアクション
日時: 2024年11月02日 16:42:10
チャンネル: #engineering
投稿者: 鈴木一郎
内容: バグ修正ありがとうございました！おかげで無事リリースできました...
リンク: https://your-workspace.slack.com/archives/C1617181/p1617181920212223

================================================================================
統計情報:
  - 分析した投稿数: 45 件
  - 総リアクション数: 387 個
  - 平均リアクション数: 8.6 個
  - 投稿期間: 2024-10-01 〜 2024-12-30
================================================================================
```

## トラブルシューティング

### `not_allowed_token_type` エラー

User Tokenではなく、Bot Token（`xoxb-`で始まる）を使用してください。

### レート制限エラー

大量のメッセージを処理する際にレート制限に引っかかる場合があります。少し時間を置いてから再実行してください。

### 検索結果が0件

- 絵文字名が正しいか確認（`:pray:` ではなく `pray`）
- 日付範囲が適切か確認
