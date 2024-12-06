import json
import os
import boto3
import logging
from typing import Dict, Any, List,Optional
from lib.slack import SlackManager
from lib.db import DynamoDBManager
from lib.db import UserInfo
from interactive_notification import handle_home_opened

# ロガーの設定
logger = logging.getLogger()
logger.setLevel(logging.INFO)

dynamodb: boto3.resources.base.ServiceResource = boto3.resource('dynamodb')
db_manager: DynamoDBManager = DynamoDBManager(dynamodb)



def handle_event_notification(message: Dict[str, Any]) -> None:
    """イベントトピックからの通知を処理"""
    logger.info("イベント通知を受信: %s", message)
    
    event_id: str = message.get('event_id')
    user_id: Optional[str] = message.get('user_id')
    team_id: str = message.get('team_id')
    logger.info("ワークスペース情報を取得中: team_id=%s", team_id)
    workspace_data: Dict[str, Any] = db_manager.get_workspace_data(team_id)
    slack_token: str = workspace_data.get('access_token') 
    if not slack_token:
        logger.error("ワークスペースのBotトークンが見つかりません: team_id=%s", team_id)
        return
    
    logger.info("slack_token:" f"{slack_token}")
    slack_manager: SlackManager = SlackManager(slack_token)

    def check_and_save_user_profile(user_id: str) -> None:
            user_data: Optional[UserInfo] = db_manager.get_user_data(user_id)
            
            if not user_data or user_data.has_empty_fields:
                user_profile: Optional[Dict[str, Any]] = slack_manager.get_user_profile(user_id)
                if user_profile:
                    db_manager.save_or_update_user_profile(user_profile)
    check_and_save_user_profile(user_id)

    if event_id == 'home_opened':
        logger.info("ホームタブが開かれました: user_id=%s", user_id)
        slack_manager.join_all_public_channels()
        handle_home_opened(user_id, slack_manager)
        return

    if event_id == 'app_installed':
        logger.info("アプリがインストールされました: team_id=%s", team_id)
        slack_manager.join_all_public_channels()
        return

    if event_id in ['team_join', 'user_profile_change']:
        user_profile = message.get('user_profile')
        if user_profile:
            db_manager.save_or_update_user_profile(user_profile)
            logger.info("ユーザープロファイルを保存/更新しました: user_id=%s", user_profile['id'])

    if event_id == 'point_give':
        message_text = message.get('message', '')  # メッセージを取得
        mentions: List[str] = message.get('mentions', [])
        if not mentions:
            logger.error("メンションが見つかりません")
            return
        
        logger.info("ポイントを付与中: user_id=%s, mentions=%s", user_id, mentions)
        
        # 受信者の情報を確認し、存在しない場合は保存
        for mention in mentions:
            check_and_save_user_profile(mention)

        result: Dict[str, Any] = db_manager.add_points(user_id, mentions, message=message_text)

        if result['success']:
            logger.info("ポイント付与成功: user_id=%s", user_id)
            from_user_data: UserInfo = db_manager.get_user_data(user_id)
            from_user_name = from_user_data.user_name

            for mention in mentions:
                user_data: UserInfo = db_manager.get_user_data(mention)
                message: str = (
                    f"🎉 ポイントを受け取りました！\n"
                    f"*From:* {from_user_name}\n"
                    f"*現在の合計ポイント:* {user_data.total_points}ポイント"
                )
                logger.info("受信者へDM送信: mention=%s", mention)
                slack_manager.send_dm(mention, message)

            # 送信者への通知
            sender_message: str = (
                f"✅ {len(mentions)}人にポイントを付与しました\n"
                f"*残りの付与可能ポイント:* {5 - result['daily_points_given']}ポイント"
            )
            logger.info("送信者へDM送信: user_id=%s", user_id)
            slack_manager.send_dm(user_id, sender_message)
        
        else:
            logger.error("ポイント付与失敗: user_id=%s, error=%s", user_id, result['error_message'])
            # ポイント付与失敗の通知
            error_message: str = (
                "⚠️ ポイントを付与できませんでした\n"
                f"*理由:* {result['error_message']}\n"
                f"*残りの付与可能ポイント:* {5 - result['daily_points_given']}ポイント"
            )
            slack_manager.send_dm(user_id, error_message)
