import json
import os
import boto3
from lib.db import DynamoDBManager
from lib.slack import SlackManager

dynamodb = boto3.resource('dynamodb')
sns = boto3.client('sns')
db_manager = DynamoDBManager(dynamodb)
slack_manager = SlackManager(os.environ['SLACK_BOT_TOKEN'])

def lambda_handler(event, context):
    try:
        # Slackイベントの検証
        body = json.loads(event['body'])
        if 'challenge' in body:
            return {
                'statusCode': 200,
                'body': json.dumps({'challenge': body['challenge']})
            }

        # メッセージ処理
        event_data = body['event']
        if event_data['type'] != 'message':
            return {'statusCode': 200}

        # メンションとポイント付与の処理
        mentions = slack_manager.extract_mentions(event_data['text'])
        if not mentions:
            return {'statusCode': 200}

        # ポイント付与処理
        user_id = event_data['user']
        result = db_manager.add_points(user_id, mentions)

        # 通知送信
        sns.publish(
            TopicArn=os.environ['SNS_TOPIC_ARN'],
            Message=json.dumps({
                'user_id': user_id,
                'mentions': mentions,
                'result': result
            })
        )

        return {'statusCode': 200}

    except Exception as e:
        print(f"Error: {str(e)}")
        return {'statusCode': 500}