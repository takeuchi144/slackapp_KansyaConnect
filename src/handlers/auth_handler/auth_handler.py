import os
import json
import boto3
import time
import logging
from typing import Dict, Any
from urllib.parse import parse_qs
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError

# ロガーの設定
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# DynamoDBクライアントの初期化
dynamodb = boto3.resource('dynamodb')
auth_table = dynamodb.Table(f"{os.environ['STACK_NAME']}-auth")

def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    try:
        # クエリパラメータからcodeを取得
        query_params = event.get('queryStringParameters', {})
        if not query_params or 'code' not in query_params:
            logger.error("認証コードが見つかりません")
            return {
                'statusCode': 400,
                'body': json.dumps({'error': 'Authorization code not found'})
            }

        code = query_params['code']
        logger.info("認証コードを受信: %s", code)
        
        # Slack OAuth APIを呼び出してアクセストークンを取得
        client = WebClient()
        logger.info("Slack OAuth APIを呼び出し中...")
        oauth_response = client.oauth_v2_access(
            client_id=os.environ.get('SLACK_CLIENT_ID'),
            client_secret=os.environ.get('SLACK_CLIENT_SECRET'),
            code=code
        )
        logger.info("OAuth応答を受信: %s", oauth_response)

        # チーム情報を取得してドメインを取得
        access_token = oauth_response['access_token']
        client = WebClient(token=access_token)
        team_info_response = client.team_info()
        team_domain = team_info_response['team']['domain']
        logger.info("チームドメインを取得: %s", team_domain)

        # 認証情報をDynamoDBに保存
        team_id = oauth_response['team']['id']
        workspace_id = oauth_response['team']['enterprise_id'] if 'enterprise_id' in oauth_response['team'] else team_id
        current_time = int(time.time())
        
        logger.info("DynamoDBに認証情報を保存中: team_id=%s, workspace_id=%s", team_id, workspace_id)
        auth_table.put_item(
            Item={
                'team_id': team_id,
                'workspace_id': workspace_id,
                'access_token': oauth_response['access_token'],
                'team_name': oauth_response['team']['name'],
                'created_at': current_time
            }
        )

        # ワークスペースドメイン取得
        app_id = os.environ.get('SLACK_APP_ID')

        # SlackアプリのURL
        slack_app_url = f"https://{team_domain}.slack.com/apps/{app_id}"

        logger.info("認証が正常に完了しました")
        return {
            'statusCode': 302,
            'headers': {
                'Location': slack_app_url
            }
        }

    except SlackApiError as e:
        logger.error("Slack APIエラー: %s", str(e))
        return {
            'statusCode': 500,
            'body': json.dumps({'error': 'Slack API error occurred'})
        }
    except Exception as e:
        logger.error("エラーが発生しました: %s", str(e), exc_info=True)
        return {
            'statusCode': 500,
            'body': json.dumps({'error': 'Internal server error'})
        }
