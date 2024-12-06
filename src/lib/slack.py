from typing import List, Dict, Optional, Any,Tuple
import re
from slack_sdk.errors import SlackApiError
from slack_sdk import WebClient
import logging

class SlackManager:
    def __init__(self, token: str) -> None:
        self.client = WebClient(token=token)
        self.logger = logging.getLogger(__name__)
        self.logger.setLevel(logging.INFO)
        handler = logging.StreamHandler()
        handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
        self.logger.addHandler(handler)

    def send_dm(self, user_id: str, message: str) -> bool:
        """DMの送信"""
        try:
            # DMチャンネルのオープン
            response: Dict[str, Any] = self.client.conversations_open(users=[user_id])
            channel_id: str = response['channel']['id']

            # メッセージ送信
            self.client.chat_postMessage(
                channel=channel_id,
                text=message,
                parse='full'
            )
            return True

        except SlackApiError as e:
            self.logger.error(f"Error sending DM: {str(e)}")
            return False

    def publish_home_tab(self, user_id: str, points: int = 0, remaining_points: int = 5) -> None:
        """ホームタブの表示"""
        try:
            home_view = {
                "type": "home",
                "blocks": [
                    {
                        "type": "section",
                        "text": {
                            "type": "mrkdwn",
                            "text": "*ありがとうポイント 管理画面*"
                        }
                    },
                    {
                        "type": "section",
                        "text": {
                            "type": "mrkdwn",
                            "text": "このアプリが招待されているチャンネルで誰かにメンション付きでありがとうと伝えるとポイントがあげられます 😊"
                        }
                    },
                    {
                        "type": "divider"
                    },
                    {
                        "type": "section",
                        "text": {
                            "type": "mrkdwn",
                            "text": f"*現在のポイント:* {points}ポイント"
                        }
                    },
                    {
                        "type": "section",
                        "text": {
                            "type": "mrkdwn",
                            "text": f"*今日の残り送付ポイント:* {remaining_points}回"
                        }
                    },
                    {
                        "type": "actions",
                        "elements": [
                            {
                                "type": "button",
                                "text": {
                                    "type": "plain_text", 
                                    "text": "📊 履歴確認",
                                    "emoji": True
                                },
                                "action_id": "view_history"
                            }
                        ]
                    }
                ]
            }
            self.client.views_publish(
                user_id=user_id,
                view=home_view
            )
        except SlackApiError as e:
            self.logger.error(f"Error publishing home tab: {str(e)}")

    @classmethod
    def extract_mentions(cls, text: str) -> Tuple[List[str], str]:
        """メンションの抽出"""
        # メンションパターン: <@USER_ID>
        mention_pattern: str = r'<@([A-Z0-9]+)>'
        mentions: List[str] = re.findall(mention_pattern, text)
        text_without_mentions: str = re.sub(mention_pattern, '', text)
        return list(set(mentions)), text_without_mentions  # 重複を除去

    def get_user_info(self, user_id: str) -> Optional[Dict[str, Any]]:
        """ユーザー情報の取得"""
        try:
            response: Dict[str, Any] = self.client.users_info(user=user_id)
            return response['user']
        except SlackApiError as e:
            self.logger.error(f"Error getting user info: {str(e)}")
            return None

    def post_message(self, channel_id: str, message: str) -> Optional[Dict[str, Any]]:
        """チャンネルへのメッセージ送信"""
        try:
            response: Dict[str, Any] = self.client.chat_postMessage(
                channel=channel_id,
                text=message,
                parse='full'
            )
            return response
        except SlackApiError as e:
            self.logger.error(f"Error posting message: {str(e)}")
            return None

    @classmethod
    def format_message(cls, message_type: str, data: Dict[str, Any]) -> str:
        """メッセージのフォーマット"""
        if message_type == 'points_added':
            return (
                f"🎉 <@{data['from_user']}>から「ありがとう」ポイントを受け取りました！\n"
                f"*現在の合計ポイント:* {data['total_points']}ポイント"
            )
        elif message_type == 'limit_exceeded':
            return (
                "⚠️ ポイント付与の上限に達しました\n"
                "毎日0時にリセットされます"
            )
        else:
            return message_type  # カスタムメッセージをそのまま返す

    def get_workspace_info(self) -> Optional[Dict[str, Any]]:
        """ワークスペース情報の取得"""
        try:
            response: Dict[str, Any] = self.client.team_info()
            return response['team']
        except SlackApiError as e:
            self.logger.error(f"Error getting workspace info: {str(e)}")
            return None

    def join_all_public_channels(self) -> None:
        """公開チャンネルにすべて参加"""
        try:
            response: Dict[str, Any] = self.client.conversations_list(types='public_channel')
            channels: List[Dict[str, Any]] = response['channels']
            for channel in channels:
                self.client.conversations_join(channel=channel['id'])
                self.logger.info(f"Joined channel: {channel['name']}")
        except SlackApiError as e:
            self.logger.error(f"Error joining channels: {str(e)}")

    def get_user_profile(self, user_id: str) -> Optional[Dict[str, Any]]:
        """ユーザーのプロファイル情報を取得"""
        try:
            response: Dict[str, Any] = self.client.users_info(user=user_id)
            self.logger.info(f"response: {response}")
            user_info = response['user']
            profile = user_info['profile']
            return {
                'user_id': user_info['id'],
                'team_id': user_info['team_id'],
                'user_name': user_info['name'],
                'real_name': profile['real_name'],
                'display_name': profile['display_name'],
                'email': profile.get('email', '')
            }
        except SlackApiError as e:
            self.logger.error(f"Error getting user profile: {str(e)}")
            return None
