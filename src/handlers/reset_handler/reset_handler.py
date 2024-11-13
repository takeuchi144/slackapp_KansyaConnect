import boto3
import datetime
from lib.db import DynamoDBManager

dynamodb = boto3.resource('dynamodb')
db_manager = DynamoDBManager(dynamodb)

def lambda_handler(event, context):
    try:
        # 日付の取得
        today = datetime.datetime.now().strftime('%Y-%m-%d')
        
        # 全ユーザーの日次ポイントをリセット
        result = db_manager.reset_daily_points(today)
        
        return {
            'statusCode': 200,
            'body': {
                'message': 'Daily points reset successfully',
                'users_reset': result['users_reset']
            }
        }
        
    except Exception as e:
        print(f"Error resetting daily points: {str(e)}")
        return {
            'statusCode': 500,
            'body': {
                'error': str(e)
            }
        }