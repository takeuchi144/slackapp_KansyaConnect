import json
import os
import boto3
import logging
from typing import Dict, Any, List
from lib.db import DynamoDBManager
from lib.slack import SlackManager
from boto3.resources.base import ServiceResource

# ロガーの設定
logger = logging.getLogger()
logger.setLevel(logging.INFO)

dynamodb: ServiceResource = boto3.resource('dynamodb')
sns = boto3.client('sns')
db_manager: DynamoDBManager = DynamoDBManager(dynamodb)

def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    try:
        logger.info("イベントを受信しました: %s", event)
        
        # Slackイベントの検証
        body: Dict[str, Any] = json.loads(event['body'])
        logger.info("リクエストボディ: %s", body)
        
        # challengeリクエストの処理
        if 'challenge' in body:
            logger.info("Challengeリクエストを処理します")
            return {
                'statusCode': 200,
                'body': json.dumps({'challenge': body['challenge']})
            }

        # 重複リクエストのチェック
        if 'X-Slack-Retry-Num' in event['headers']:
            logger.info("重複リクエストを検出しました")
            return {
                'statusCode': 200,
                'body': json.dumps({'message': 'Duplicate request'})
            }

        # イベント処理
        event_data: Dict[str, Any] = body['event']
        event_type: str = event_data['type']
        team_id: str = body['team_id']

        # SlackManagerのインスタンス化
        workspace_data: Dict[str, Any] = db_manager.get_workspace_data(team_id)
        slack_token: str = workspace_data.get('access_token')
        if not slack_token:
            logger.error("ワークスペースのBotトークンが見つかりません: team_id=%s", team_id)
            return {'statusCode': 500}
        
        slack_manager: SlackManager = SlackManager(slack_token)

        if event_type == 'app_home_opened':
            logger.info("ホームタブが開かれました: user_id=%s", event_data['user'])
            message_data = {
                'event_id': 'home_opened',
                'user_id': event_data['user'],
                'team_id': team_id
            }
            logger.info("SNSメッセージを送信: %s", message_data)
            sns.publish(
                TopicArn=os.environ['SNS_POINTS_TOPIC_ARN'],
                Message=json.dumps(message_data)
            )
            return {'statusCode': 200}

        elif event_type == 'message':
            # メンションとポイント付与の処理
            mentions_and_text = slack_manager.extract_mentions(event_data['text'])
            mentions: List[str] = mentions_and_text[0]
            extracted_text: str = mentions_and_text[1]
            if not mentions:
                logger.info("メンションが見つかりませんでした")
                return {'statusCode': 200}
            
            # "ありがとう"のチェック
            if "ありがとう" not in extracted_text:
                logger.info("メッセージに「ありがとう」が含まれていません")
                return {'statusCode': 200}
            
            logger.info("検出されたメンション: %s", mentions)
            
            # ワークスペース情報の取得
            workspace_info: Dict[str, Any] = slack_manager.get_workspace_info()
            logger.info("ワークスペース情報を取得: %s", workspace_info)
            
            # SNSにポイント付与リクエストを送信
            user_id: str = event_data['user']
            message_data = {
                'event_id': 'point_give',
                'user_id': user_id,
                'mentions': mentions,
                'team_id': team_id,
                'workspace_name': workspace_info.get('name', ''),
                'workspace_domain': workspace_info.get('domain', ''),
                'message': extracted_text  # メッセージを追加
            }
            logger.info("SNSメッセージを送信: %s", message_data)
            
            sns.publish(
                TopicArn=os.environ['SNS_POINTS_TOPIC_ARN'],
                Message=json.dumps(message_data)
            )
            return {'statusCode': 200}

        elif event_type == 'app_installed':
            logger.info("アプリがインストールされました: team_id=%s", team_id)
            message_data = {
                'event_id': 'app_installed',
                'user_id': None,
                'team_id': team_id
            }
            logger.info("SNSメッセージを送信: %s", message_data)
            sns.publish(
                TopicArn=os.environ['SNS_POINTS_TOPIC_ARN'],
                Message=json.dumps(message_data)
            )
            return {'statusCode': 200}

        elif event_type == 'team_join' or event_type == 'user_profile_change':
            user_info = event_data['user']
            message_data = {
                'event_id': event_type,
                'user_id': user_info['id'],
                'team_id': user_info['team_id'],
                'user_profile': user_info
            }
            logger.info("SNSメッセージを送信: %s", message_data)
            sns.publish(
                TopicArn=os.environ['SNS_POINTS_TOPIC_ARN'],
                Message=json.dumps(message_data)
            )
            return {'statusCode': 200}

        else:
            logger.info("未対応のイベントタイプを受信: %s", event_type)
            return {'statusCode': 200}

    except Exception as e:
        logger.error("エラーが発生しました: %s", str(e), exc_info=True)
        return {'statusCode': 500}