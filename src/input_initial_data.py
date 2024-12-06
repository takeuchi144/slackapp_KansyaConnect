import os
import boto3
from datetime import datetime

def handler(event, context):
    try:
        #event['RequestType'] in ['Create', 'Update']:
        dynamodb = boto3.resource('dynamodb')
        table = dynamodb.Table(f'{os.environ['STACK_NAME']}-auth')
        
            # 初期データ投入
        initial_data = {
            'workspace_id': os.environ.get('INITIAL_TEAM_ID'),
            'access_token': os.environ.get('SLACK_BOT_TOKEN') ,
            'team_name': 'default',
            'created_at': int((datetime.now().timestamp() + 86400))  # 24時間後のTTL
            }
        
        table.put_item(Item=initial_data)
        
        return {
                'statusCode': 200,
                'body': 'Initial data successfully inserted'
            }
        
    except Exception as e:
        print(f"Error: {str(e)}")
        return {
            'statusCode': 500,
            'body': f'Error inserting initial data: {str(e)}'
            }