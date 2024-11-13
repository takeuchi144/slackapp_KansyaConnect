import json
import os
import boto3
from lib.slack import SlackManager
from lib.db import DynamoDBManager

slack_manager = SlackManager(os.environ['SLACK_BOT_TOKEN'])
dynamodb = boto3.resource('dynamodb')
db_manager = DynamoDBManager(dynamodb)

def lambda_handler(event, context):
    try:
        # SNSメッセージの解析
        message = json.loads(event['Records'][0]['Sns']['Message'])
        user_id = message['user_id']
        mentions = message['mentions']
        result = message['result']

        # 結果に基づいて通知メッセージを作成
        if result['success']:
            # ポイント付与成功の通知
            for mention in mentions:
                user_data = db_manager.get_user_data(mention)
                message = (
                    f"🎉 ポイントを受け取りました！\n"
                    f"*From:* <@{user_id}>\n"
                    f"*現在の合計ポイント:* {user_data['total_points']}ポイント"
                )
                slack_manager.send_dm(mention, message)

            # 送信者への通知
            sender_message = (
                f"✅ {len(mentions)}人にポイントを付与しました\n"
                f"*残りの付与可能ポイント:* {5 - result['daily_points_given']}ポイント"
            )
            slack_manager.send_dm(user_id, sender_message)
        
        else:
            # ポイント付与失敗の通知
            error_message = (
                "⚠️ ポイントを付与できませんでした\n"
                f"*理由:* {result['error_message']}\n"
                f"*残りの付与可能ポイント:* {5 - result['daily_points_given']}ポイント"
            )
            slack_manager.send_dm(user_id, error_message)

        return {
            'statusCode': 200,
            'body': json.dumps({'message': 'Notifications sent successfully'})
        }

    except Exception as e:
        print(f"Error processing notification: {str(e)}")
        return {
            'statusCode': 500,
            'body': json.dumps({'error': str(e)})
        }