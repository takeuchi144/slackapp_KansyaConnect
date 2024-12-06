import json
import os
import boto3
import logging
from typing import Dict, Any, List

from event_notification import handle_event_notification
from interactive_notification import handle_interactive_notification

# ロガーの設定
logger = logging.getLogger()
logger.setLevel(logging.INFO)

def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    try:
        # SNSメッセージの解析
        sns_message = event['Records'][0]['Sns']
        topic_arn: str = sns_message['TopicArn']
        message: Dict[str, Any] = json.loads(sns_message['Message'])
        logger.info("SNSメッセージを受信: topic_arn=%s, message=%s", topic_arn, message)

        # スタック名の取得
        stack_name = os.environ['STACK_NAME']
        event_topic = f"{stack_name}-events" # EventTopicと一致
        interactive_topic = f"{stack_name}-interactive" # InteractiveTopicと一致
        logger.info("トピック名を設定: event_topic=%s, interactive_topic=%s", event_topic, interactive_topic)

        # トピックに応じて処理を分岐
        if topic_arn.endswith(event_topic):
            # イベントトピックの場合
            logger.info("イベントトピックの処理を開始")
            required_fields = {'event_id', 'user_id', 'team_id'}
            if not required_fields.issubset(message.keys()):
                missing_fields = required_fields - set(message.keys())
                logger.error("必須フィールドが不足しています: %s", missing_fields)
                raise ValueError(f"Required fields missing in event message: {missing_fields}")
            handle_event_notification(message)

        elif topic_arn.endswith(interactive_topic):
            # インタラクティブトピックの場合
            logger.info("インタラクティブトピックの処理を開始")
            handle_interactive_notification(message)
        else:
            logger.error("不明なトピックARN: %s", topic_arn)
            raise ValueError(f"Unknown topic ARN: {topic_arn}. Expected either {event_topic} or {interactive_topic}")

        logger.info("通知の処理が正常に完了しました")
        return {
            'statusCode': 200,
            'body': json.dumps({'message': 'Notifications sent successfully'})
        }

    except ValueError as e:
        logger.error("バリデーションエラー: %s", str(e))
        return {
            'statusCode': 400,
            'body': json.dumps({'error': str(e)})
        }
    except Exception as e:
        logger.error("通知の処理中にエラーが発生しました: %s", str(e), exc_info=True)
        return {
            'statusCode': 500,
            'body': json.dumps({'error': 'Internal server error'})
        }