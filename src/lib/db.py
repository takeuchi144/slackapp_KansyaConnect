import os 
import boto3
from typing import Dict, List, Any, Optional,Union
import uuid
from datetime import datetime
from boto3.dynamodb.conditions import Key, Attr
from boto3.resources.base import ServiceResource
import logging

from lib.user_info import UserInfo
# ロガーの設定
logger = logging.getLogger()
logger.setLevel(logging.INFO)



class DynamoDBManager:
    def __init__(self, dynamodb: ServiceResource, stack_name: Optional[str] = None) -> None:
        self.dynamodb: ServiceResource = dynamodb
        self.stack_name: str = stack_name or os.environ['STACK_NAME']
        self.users_table = dynamodb.Table(f'{self.stack_name}-users')
        self.transactions_table = dynamodb.Table(f'{self.stack_name}-transactions')
        self.workspaces_table = dynamodb.Table(f'{self.stack_name}-auth')
        logger.info("DynamoDBManager initialized with stack name: %s", self.stack_name)

    def get_user_data(self, user_id: str) -> Optional[UserInfo]:
        """ユーザーデータの取得"""
        logger.info("Fetching user data for user_id: %s", user_id)
        response: Dict[str, Any] = self.users_table.get_item(
            Key={'user_id': user_id}
        )
        user_data = response.get('Item')
        if not user_data:
            logger.info("User data not found for user_id: %s", user_id)
            return None
        user_info = UserInfo.from_dict(user_data)
        logger.info("User data fetched: %s", user_info.to_dict())
        return user_info

    def get_workspace_data(self, team_id: str) -> Dict[str, Any]:
        """ワークスペースデータの取得"""
        logger.info("Fetching workspace data for team_id: %s", team_id)
        response: Dict[str, Any] = self.workspaces_table.get_item(
            Key={'workspace_id':team_id}
        )
        workspace_data = response.get('Item', {})
        logger.info("Workspace data fetched: %s", workspace_data)
        return workspace_data

    def get_user_transactions(self, user_id: str) -> List[Dict[str, Any]]:
        """ユーザーのトランザクション履歴を取得"""
        logger.info("Fetching transactions for user_id: %s", user_id)
        transactions = []
        
        # 受け取ったポイントの取得
        received = self.transactions_table.scan(
            FilterExpression=Attr('to_users').contains(user_id)
        )
        for tx in received.get('Items', []):
            transactions.append({
                'type': 'received',
                'from_user': tx['from_user'],
                'points': tx['points'],
                'timestamp': tx['timestamp'],
                'message': tx.get('message', '')
            })

        # 送信したポイントの取得
        sent = self.transactions_table.scan(
            FilterExpression=Attr('from_user').eq(user_id)
        )
        for tx in sent.get('Items', []):
            for to_user in tx['to_users']:
                transactions.append({
                    'type': 'sent',
                    'to_user': to_user,
                    'points': tx['points'],
                    'timestamp': tx['timestamp'],
                    'message': tx.get('message', '')
                })

        # タイムスタンプでソート
        transactions.sort(key=lambda x: x['timestamp'], reverse=True)
        logger.info("Transactions fetched and sorted: %s", transactions)
        return transactions

    def add_points(self, from_user: str, to_users: List[str], message: str = '') -> Dict[str, Any]:
        # from_user が to_users に含まれていたら除外
        to_users = [user for user in to_users if user != from_user]
        
        # to_users が空になったら return
        if not to_users:
            logger.info("No valid recipients after excluding the sender: %s", from_user)
            return {
                'success': False,
                'error_message': '送信者が受信者と同一でした'
            }
        
        """ポイントの付与"""
        logger.info("Adding points from user: %s to users: %s", from_user, to_users)
        max_retries = 3
        attempt = 0

        while attempt < max_retries:
            try:
                # 送信者の日次ポイント確認
                sender_data: UserInfo = self.get_user_data(from_user)
                daily_points_given: int = sender_data.daily_points_given
                logger.info("Sender's daily points: %d", daily_points_given)
                
                if daily_points_given + len(to_users) > 5:
                    logger.warning("Daily points limit exceeded for user: %s", from_user)
                    return {
                        'success': False,
                        'error_message': '本日の付与可能ポイントを超過しています',
                        'daily_points_given': daily_points_given
                    }

                # トランザクションID生成
                transaction_id: str = str(uuid.uuid4())
                timestamp: str = datetime.now().isoformat()
                logger.info("Generated transaction_id: %s at timestamp: %s", transaction_id, timestamp)

                # トランザクションアイテムの準備
                transact_items = []

                # 送信者の日次ポイント更新アイテム
                transact_items.append({
                    'Update': {
                        'TableName': self.users_table.name,
                        'Key': {'user_id': from_user},
                        'UpdateExpression': 'SET daily_points_given = if_not_exists(daily_points_given, :zero) + :points',
                        'ConditionExpression': 'attribute_not_exists(daily_points_given) OR daily_points_given = :current_daily_points',
                        'ExpressionAttributeValues': {
                            ':zero': 0,
                            ':points': len(to_users),
                            #':maxDaily': 5,
                            ':current_daily_points': daily_points_given,
                        }
                    }
                })
                logger.info("Prepared transaction item for sender: %s with daily_points_given: %d", from_user, daily_points_given)

                # 各受信者へのポイント付与アイテム
                for to_user in to_users:
                    receiver_data: UserInfo = self.get_user_data(to_user)
                    current_points = receiver_data.total_points
                    
                    transact_items.append({
                        'Update': {
                            'TableName': self.users_table.name,
                            'Key': {'user_id': to_user},
                            'UpdateExpression': 'SET total_points = if_not_exists(total_points, :zero) + :points',
                            'ConditionExpression': 'attribute_not_exists(total_points) OR total_points = :current_points',
                            'ExpressionAttributeValues': {
                                ':zero': 0,
                                ':points': 1,
                                ':current_points': current_points,
                            }
                        }
                    })
                    logger.info("Prepared transaction item for receiver: %s with total_points: %d", to_user, current_points)

                # トランザクション記録アイテム
                transact_items.append({
                    'Put': {
                        'TableName': self.transactions_table.name,
                        'Item': {
                            'transaction_id': transaction_id,
                            'from_user': from_user,
                            'to_users': to_users,
                            'points': 1,
                            'timestamp': timestamp,
                            'message': message
                        }
                    }
                })
                logger.info("Prepared transaction record item")

                # トランザクション実行
                self.dynamodb.meta.client.transact_write_items(
                    TransactItems=transact_items
                )
                logger.info("Transaction executed successfully")

                return {
                    'success': True,
                    'daily_points_given': daily_points_given + len(to_users),
                    'transaction_id': transaction_id
                }

            except self.dynamodb.meta.client.exceptions.TransactionCanceledException as e:
                attempt += 1
                logger.warning(f"Transaction cancelled, retrying {attempt}/{max_retries}: {str(e)}")
                if attempt >= max_retries:
                    logger.error("Max retries reached. Transaction failed.")
                    return {
                        'success': False,
                        'error_message': 'トランザクションが競合により中断されました。再度お試しください。',
                        'daily_points_given': daily_points_given
                    }
            except Exception as e:
                logger.error(f"Error adding points: {str(e)}")
                return {
                    'success': False,
                    'error_message': 'データベース更新中にエラーが発生しました',
                    'daily_points_given': daily_points_given
                }

    def reset_daily_points(self, date: str) -> Dict[str, Any]:
        """日次ポイントのリセット"""
        try:
            # 全ユーザーのスキャン
            response: Dict[str, Any] = self.users_table.scan()
            users: List[Dict[str, Any]] = response['Items']
            users_reset: int = 0

            # バッチ更新用のアイテムリスト
            for user in users:
                self.users_table.update_item(
                    Key={'user_id': user['user_id']},
                    UpdateExpression="SET daily_points_given = :zero, last_reset_date = :date",
                    ExpressionAttributeValues={
                        ':zero': 0,
                        ':date': date
                    }
                )
                users_reset += 1

            return {
                'success': True,
                'users_reset': users_reset
            }

        except Exception as e:
            logger.error(f"Error resetting daily points: {str(e)}")
            return {
                'success': False,
                'error_message': str(e)
            }

    def get_points_history(self, user_id: str) -> Dict[str, List[Dict[str, Any]]]:
        """ポイント履歴の取得"""
        try:
            # 受け取ったポイントの履歴
            received: Dict[str, Any] = self.transactions_table.scan(
                FilterExpression=Attr('to_users').contains(user_id)
            )

            # 送信したポイントの履歴
            sent: Dict[str, Any] = self.transactions_table.scan(
                FilterExpression=Attr('from_user').eq(user_id)
            )

            return {
                'received': received['Items'],
                'sent': sent['Items']
            }

        except Exception as e:
            logger.error(f"Error getting points history: {str(e)}")
            return {
                'received': [],
                'sent': []
            }

    def save_or_update_user_profile(self, user_profile: Union[Dict[str, Any], UserInfo]) -> None:
        """ユーザープロファイルを保存または更新"""
        try:
            if isinstance(user_profile, dict):
                user_info: UserInfo = UserInfo.from_dict(user_profile)
            else:
                user_info: UserInfo = user_profile

            existing_user_data: Optional[UserInfo] = self.get_user_data(user_info.user_id)
            

            # 既存のデータがある場合は更新、ない場合は新規登録
            if existing_user_data :
                user_info.total_points = existing_user_data.total_points
                user_info.daily_points_given = existing_user_data.daily_points_given
                self.users_table.update_item(
                    Key={'user_id': user_info.user_id},
                    UpdateExpression=(
                        "SET team_id = :team_id, "
                        "user_name = :user_name, "
                        "real_name = :real_name, "
                        "display_name = :display_name, "
                        "email = :email, "
                        "total_points = :total_points, "
                        "daily_points_given = :daily_points_given"
                    ),
                    ExpressionAttributeValues={
                        ':team_id': user_info.team_id,
                        ':user_name': user_info.user_name,
                        ':real_name': user_info.real_name,
                        ':display_name': user_info.display_name,
                        ':email': user_info.email,
                        ':total_points': user_info.total_points,
                        ':daily_points_given': user_info.daily_points_given
                    }
                )
            else:
                self.users_table.put_item(
                    Item=user_info.to_dict()
                )
            logger.info("User profile saved/updated for user_id: %s", user_info.user_id)
        except Exception as e:
            logger.error(f"Error saving/updating user profile: {str(e)}")

    def get_users_data(self, user_ids: List[str]) -> List[Optional[UserInfo]]:
        """複数のユーザー情報を取得"""
        users_data = []
        for user_id in user_ids:
            user_data: Optional[UserInfo] = self.get_user_data(user_id)
            if user_data:
                users_data.append(user_data)
        return users_data