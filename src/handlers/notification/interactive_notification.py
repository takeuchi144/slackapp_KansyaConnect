import json
import os
import boto3
import logging
from typing import Dict, Any, List, Optional
from lib.slack import SlackManager
from lib.db import DynamoDBManager
from lib.user_info import UserInfo
# ロガーの設定
logger = logging.getLogger()
logger.setLevel(logging.INFO)

dynamodb: boto3.resources.base.ServiceResource = boto3.resource('dynamodb')
db_manager: DynamoDBManager = DynamoDBManager(dynamodb)

def handle_home_opened(user_id: str, slack_manager: SlackManager) -> None:

    logger.info("ユーザー情報を取得中: user_id=%s", user_id)
    user_data: Optional[UserInfo] = db_manager.get_user_data(user_id)
    if not user_data or user_data.has_empty_fields:
        logger.error("ユーザーデータが見つかりません: user_id=%s", user_id)
        return
    total_points: int = user_data.total_points
    remaining_points: int = 5 - user_data.daily_points_given
    
    logger.info("ホームタブを更新中: user_id=%s, total_points=%d, remaining_points=%d", 
                user_id, total_points, remaining_points)
    slack_manager.publish_home_tab(
        user_id=user_id,
        points=total_points,
        remaining_points=remaining_points
    )

def handle_view_history(user_id: str, team_id: str) -> None:
    """ポイント履歴の表示処理"""
    # ワークスペースごとのトークンを取得
    logger.info("ワークスペース情報を取得中: team_id=%s", team_id)
    workspace_data: Dict[str, Any] = db_manager.get_workspace_data(team_id)
    slack_token: str = workspace_data.get('access_token')
    
    if not slack_token:
        logger.error("ワークスペースのBotトークンが見つかりません: team_id=%s", team_id)
        return
        
    slack_manager: SlackManager = SlackManager(slack_token)
    
    # ユーザー情報を取得
    
    
    logger.info("ユーザーの取引履歴を取得中: user_id=%s", user_id)
    transactions: List[Dict[str, Any]] = db_manager.get_user_transactions(user_id)
    history_message: str = "📊 *ポイント履歴*\n"
    
    # トランザクションに含まれる全てのユーザーIDを収集
    user_ids = set()
    for tx in transactions:
        if tx['type'] == 'received':
            user_ids.add(tx['from_user'])
        else:
            user_ids.add(tx['to_user'])

    # ユーザー名を一括取得
    users_data: List[UserInfo] = db_manager.get_users_data(list(user_ids))
    user_names = {user.user_id: user.user_name for user in users_data}

    for tx in transactions:
        timestamp: str = tx.get('timestamp', '')
        message: str = tx.get('message', 'メッセージなし')
        
        if tx['type'] == 'received':
            from_user_name = user_names[tx['from_user']]
            history_message += (
                f"• {timestamp}\n"
                f"  {from_user_name}から{tx['points']}ポイントを受け取りました\n"
                f"  > {message}\n"
            )
        else:
            to_user_name = user_names[tx['to_user']]
            history_message += (
                f"• {timestamp}\n"
                f"  {to_user_name}に{tx['points']}ポイントを送りました\n"
                f"  > {message}\n"
            )
    
    logger.info("履歴メッセージをDMで送信中: user_id=%s", user_id)
    slack_manager.send_dm(user_id, history_message)

def handle_interactive_notification(message: Dict[str, Any]) -> None:
    """インタラクティブトピックからの通知を処理"""
    try:
        logger.info("インタラクティブ通知を受信: %s", message)
        
        # メッセージの解析
        user_id: str = message.get('user_id')
        team_id: str = message.get('team_id')
        action_id: str = message.get('action_id')
        
        if not action_id or not user_id or not team_id:
            logger.error("必須フィールドが不足しています: %s", message)
            raise ValueError("Required fields missing in message")

        if action_id == 'view_history':
            logger.info("履歴表示がリクエストされました: user_id=%s", user_id)
            handle_view_history(user_id, team_id)
        else:
            logger.warning("不明なaction_idを受信: %s", action_id)
            
    except ValueError as e:
        logger.error("バリデーションエラー: %s", str(e))
    except Exception as e:
        logger.error("インタラクティブ通知の処理中にエラーが発生: %s", str(e), exc_info=True)
        # エラーが発生した場合はユーザーに通知
        workspace_data: Dict[str, Any] = db_manager.get_workspace_data(team_id)
        if slack_token := workspace_data.get('bot_token'):
            slack_manager: SlackManager = SlackManager(slack_token)
            error_message = "⚠️ 処理中にエラーが発生しました。しばらく時間をおいて再度お試しください。"
            slack_manager.send_dm(user_id, error_message)


