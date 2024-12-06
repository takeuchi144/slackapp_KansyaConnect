import os
import json
import boto3
import logging
import urllib.parse
from typing import Dict, Any

# ロガーの設定
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# SNSクライアントの初期化
sns = boto3.client('sns')

def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    try:
        logger.info("イベントを受信しました: %s", event)
        
        # リクエストボディの解析
        decoded_body = urllib.parse.unquote(event['body'])
        
        # 'payload='の後のJSONデータを抽出
        payload_str = decoded_body.split('payload=')[1]
        
        # JSONとしてデコード
        body = json.loads(payload_str)
        logger.info("リクエストボディ: %s", body)
        
        # JSONデコード
        body = json.loads(payload_str)
        logger.info("リクエストボディ: %s", body)
        
        # 必要なフィールドを抽出
        user_id = body['user']['id']
        team_id = body['team']['id']
        action_id = body['actions'][0]['action_id']

        if not all([user_id, team_id, action_id]):
            logger.error("必須フィールドが不足しています: user_id=%s, team_id=%s, action_id=%s", 
                        user_id, team_id, action_id)
            raise ValueError("Required fields missing: user_id, team_id, action_id")

        # SNSトピックにメッセージを送信
        message = {
            'user_id': user_id,
            'team_id': team_id,
            'action_id': action_id
        }
        logger.info("SNSメッセージを送信: %s", message)
        
        sns.publish(
            TopicArn=os.environ['SNS_INTERACTIVE_TOPIC_ARN'],
            Message=json.dumps(message)
        )

        logger.info("メッセージを正常に処理しました")
        return {
            'statusCode': 200,
            'body': json.dumps({'message': 'Success'})
        }

    except ValueError as e:
        logger.error("バリデーションエラー: %s", str(e))
        return {
            'statusCode': 400, 
            'body': json.dumps({'error': str(e)})
        }
    except Exception as e:
        logger.error("エラーが発生しました: %s", str(e), exc_info=True)
        return {
            'statusCode': 500,
            'body': json.dumps({'error': 'Internal server error'})
        }
