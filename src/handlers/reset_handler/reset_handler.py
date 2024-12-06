import boto3
import datetime
from typing import Dict, Any
from lib.db import DynamoDBManager

from boto3.resources.base import ServiceResource

dynamodb: ServiceResource = boto3.resource('dynamodb')
db_manager: DynamoDBManager = DynamoDBManager(dynamodb)

def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    try:
        # 日付の取得
        today: str = datetime.datetime.now().strftime('%Y-%m-%d')
        
        # 全ユーザーの日次ポイントをリセット
        result: Dict[str, int] = db_manager.reset_daily_points(today)
        
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