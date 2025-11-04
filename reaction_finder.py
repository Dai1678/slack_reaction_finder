#!/usr/bin/env python3
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError
import sys
import os
import argparse
from datetime import datetime, timedelta
from typing import Dict, List, Optional

# 定数
DEFAULT_MAX_SEARCH_RESULTS = 100
MAX_TEXT_PREVIEW_LENGTH = 150
SEPARATOR = "=" * 80
DATE_FORMAT = '%Y-%m-%d'
DATETIME_DISPLAY_FORMAT = '%Y年%m月%d日 %H:%M:%S'
ENV_TOKEN_NAME = 'SLACK_REACTION_FINDER'


def parse_arguments():
    """コマンドライン引数をパース"""
    parser = argparse.ArgumentParser(
        description='Slackワークスペース内で特定の絵文字リアクションが多い投稿を検索します',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
日付指定の例:
  --on 2024-06-15                 2024年6月15日のみ
  --after 2024-01-01              2024年1月1日以降
  --before 2024-12-31             2024年12月31日以前
  --after 2024-01-01 --before 2024-03-31  2024年1-3月
  --days 30                       直近30日間
  --days 90 --before 2024-12-31   2024年12月31日から遡って90日間

検索件数の例:
  --max 200                       最大200件を検索対象とする
  --max 1000                      最大1000件を検索対象とする
        '''
    )
    parser.add_argument(
        'emoji',
        help='検索する絵文字名（例: pray, thanks, tada）'
    )
    parser.add_argument(
        '-n', '--top',
        type=int,
        default=3,
        help='表示する上位件数（デフォルト: 3）'
    )
    parser.add_argument(
        '-t', '--token',
        default=os.environ.get(ENV_TOKEN_NAME),
        help=f'Slack Bot Token（デフォルト: 環境変数{ENV_TOKEN_NAME}）'
    )
    parser.add_argument(
        '--on',
        help='この日付の投稿を検索（形式: YYYY-MM-DD）'
    )
    parser.add_argument(
        '--after',
        help='この日付以降の投稿を検索（形式: YYYY-MM-DD）'
    )
    parser.add_argument(
        '--before',
        help='この日付以前の投稿を検索（形式: YYYY-MM-DD）'
    )
    parser.add_argument(
        '--days',
        type=int,
        help='直近N日間の投稿を検索'
    )
    parser.add_argument(
        '--max',
        type=int,
        default=DEFAULT_MAX_SEARCH_RESULTS,
        help=f'検索対象とする最大件数（デフォルト: {DEFAULT_MAX_SEARCH_RESULTS}）'
    )
    
    args = parser.parse_args()

    # 検索件数の妥当性チェック
    if args.max < 1:
        parser.error("--max は1以上の値を指定してください")
    if args.max > 1000:
        print("警告: --max が1000を超えています。大量の検索は時間がかかる可能性があります。")

    # 日付オプションの競合チェック
    if args.on and (args.after or args.before or args.days):
        parser.error("--on は --after, --before, --days と同時に使用できません")

    return args


def validate_token(token: Optional[str]) -> None:
    """トークンの検証"""
    if not token:
        print("エラー: Slack Tokenが指定されていません")
        print(f"環境変数{ENV_TOKEN_NAME} を設定するか、-t オプションで指定してください")
        print("\n設定方法:")
        print(f"  export {ENV_TOKEN_NAME}='xoxb-your-token-here'")
        print("または")
        print("  python3 reaction_finder.py emoji -t xoxb-your-token-here")
        sys.exit(1)


def build_date_query(args) -> str:
    """日付範囲のクエリを構築"""
    date_query = ""

    # --onオプションが指定された場合
    if args.on:
        try:
            datetime.strptime(args.on, DATE_FORMAT)
            return f"on:{args.on}"
        except ValueError:
            raise ValueError("--on の日付形式が正しくありません（YYYY-MM-DD）")

    if args.days:
        if args.before:
            try:
                end_date = datetime.strptime(args.before, DATE_FORMAT)
                start_date = end_date - timedelta(days=args.days)
                date_query = f"after:{start_date.strftime(DATE_FORMAT)} before:{args.before}"
            except ValueError:
                raise ValueError("--before の日付形式が正しくありません（YYYY-MM-DD）")
        else:
            today = datetime.now()
            start_date = today - timedelta(days=args.days)
            date_query = f"after:{start_date.strftime(DATE_FORMAT)}"
    elif args.after or args.before:
        after_date = None
        before_date = None

        # 日付のパース
        if args.after:
            try:
                after_date = datetime.strptime(args.after, DATE_FORMAT)
            except ValueError:
                raise ValueError("--after の日付形式が正しくありません（YYYY-MM-DD）")
        if args.before:
            try:
                before_date = datetime.strptime(args.before, DATE_FORMAT)
            except ValueError:
                raise ValueError("--before の日付形式が正しくありません（YYYY-MM-DD）")

        # 日付の妥当性チェック
        if after_date and before_date:
            if after_date == before_date:
                # 同じ日付が指定された場合は、その日のみを検索
                date_query = f"on:{args.after}"
            elif after_date > before_date:
                raise ValueError(
                    f"日付の指定が不正です: "
                    f"--after ({args.after}) が --before ({args.before}) より後になっています。"
                    f"\n正しい順序で指定してください（例: --after 2025-02-01 --before 2025-10-31）"
                )
            else:
                date_query = f"after:{args.after} before:{args.before}"
        else:
            # どちらか一方のみ指定された場合
            if args.after:
                date_query += f"after:{args.after} "
            if args.before:
                date_query += f"before:{args.before}"
    
    return date_query.strip()


def get_user_name(client: WebClient, user_id: str) -> str:
    """ユーザーIDから表示名を取得"""
    try:
        user_info = client.users_info(user=user_id)
        return user_info["user"]["real_name"]
    except:
        return user_id


def fetch_message_details(
    client: WebClient, 
    match: Dict, 
    target_emoji: str
) -> Optional[Dict]:
    """メッセージの詳細とリアクション情報を取得"""
    try:
        msg_response = client.conversations_history(
            channel=match["channel"]["id"],
            latest=match["ts"],
            inclusive=True,
            limit=1
        )
        
        if not msg_response["messages"]:
            return None
        
        message = msg_response["messages"][0]
        
        if "reactions" not in message:
            return None
        
        for reaction in message["reactions"]:
            if reaction["name"] == target_emoji:
                username = get_user_name(client, message.get("user", ""))
                msg_datetime = datetime.fromtimestamp(float(match["ts"]))
                
                return {
                    "text": message.get("text", "(テキストなし)"),
                    "user": username,
                    "count": reaction["count"],
                    "channel_name": match["channel"]["name"],
                    "timestamp": match["ts"],
                    "datetime": msg_datetime,
                    "permalink": match["permalink"]
                }
    except SlackApiError as e:
        if e.response["error"] != "channel_not_found":
            print(f"\n⚠️ エラー: {e}")
    
    return None


def search_and_analyze(
    client: WebClient, 
    search_query: str, 
    target_emoji: str,
    max_results: int
) -> List[Dict]:
    """検索と分析を実行"""
    # Slack Search APIは1回のリクエストで最大100件まで
    # それ以上を取得する場合はページネーションが必要
    API_MAX_PER_PAGE = 100
    
    all_matches = []
    page = 1
    
    while len(all_matches) < max_results:
        # 今回取得する件数を計算
        count = min(API_MAX_PER_PAGE, max_results - len(all_matches))
        
        # Search APIで絵文字を含む投稿を検索
        search_response = client.search_messages(
            query=search_query,
            sort="timestamp",
            sort_dir="desc",
            count=count,
            page=page
        )
        
        total_matches = search_response["messages"]["total"]
        
        if page == 1:
            print(f"検索結果: {total_matches} 件の投稿が見つかりました")
            print(f"最大{max_results}件を取得して分析します...\n")
        
        matches = search_response["messages"]["matches"]
        if not matches:
            break
        
        all_matches.extend(matches)
        
        # これ以上データがない、または目標件数に到達した場合は終了
        if len(matches) < count or len(all_matches) >= max_results:
            break
        
        page += 1
    
    # max_resultsを超えた分は切り捨て
    all_matches = all_matches[:max_results]
    
    messages_with_reactions = []
    
    # 各メッセージの詳細を取得してリアクション数を確認
    for i, match in enumerate(all_matches, 1):
        print(f"処理中: {i}/{len(all_matches)}", end="\r")
        
        message_detail = fetch_message_details(client, match, target_emoji)
        if message_detail:
            messages_with_reactions.append(message_detail)
    
    print("\n")
    
    # カウント順にソート
    messages_with_reactions.sort(key=lambda x: x["count"], reverse=True)
    
    return messages_with_reactions


def print_results(messages: List[Dict], target_emoji: str, top_n: int) -> None:
    """検索結果を表示"""
    if not messages:
        print(f":{target_emoji}: リアクションが付いている投稿が見つかりませんでした")
        return
    
    print(SEPARATOR)
    print(f":{target_emoji}: リアクションが多い投稿 Top {top_n}")
    print(SEPARATOR)
    print()
    
    for i, msg in enumerate(messages[:top_n], 1):
        print(f"【第{i}位】 {msg['count']} 個のリアクション")
        print(f"日時: {msg['datetime'].strftime(DATETIME_DISPLAY_FORMAT)}")
        print(f"チャンネル: #{msg['channel_name']}")
        print(f"投稿者: {msg['user']}")
        
        text_preview = msg['text'][:MAX_TEXT_PREVIEW_LENGTH]
        if len(msg['text']) > MAX_TEXT_PREVIEW_LENGTH:
            text_preview += '...'
        print(f"内容: {text_preview}")
        print(f"リンク: {msg['permalink']}")
        print()
    
    # 統計情報
    print(SEPARATOR)
    print(f"統計情報:")
    print(f"  - 分析した投稿数: {len(messages)} 件")
    print(f"  - 総リアクション数: {sum(m['count'] for m in messages)} 個")
    print(f"  - 平均リアクション数: {sum(m['count'] for m in messages) / len(messages):.1f} 個")
    
    oldest = min(m['datetime'] for m in messages)
    newest = max(m['datetime'] for m in messages)
    print(f"  - 投稿期間: {oldest.strftime(DATE_FORMAT)} 〜 {newest.strftime(DATE_FORMAT)}")
    print(SEPARATOR)


def main():
    """メイン処理"""
    args = parse_arguments()
    
    # トークンの検証
    validate_token(args.token)
    
    # 日付クエリの構築
    try:
        date_query = build_date_query(args)
    except ValueError as e:
        print(f"エラー: {e}")
        sys.exit(1)
    
    # 検索クエリを構築
    search_query = f"has::{args.emoji}: {date_query}".strip()
    
    client = WebClient(token=args.token)
    
    print(f":{args.emoji}: リアクションが多い投稿を検索中...")
    if date_query:
        print(f"期間指定: {date_query}")
    print()
    
    try:
        messages = search_and_analyze(client, search_query, args.emoji, args.max)
        print_results(messages, args.emoji, args.top)
    except SlackApiError as e:
        print(f"Slack APIエラーが発生しました: {e.response['error']}")
        sys.exit(1)
    except Exception as e:
        print(f"予期しないエラーが発生しました: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
