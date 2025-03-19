# KansyaConnect - Slackでの感謝の気持ちを共有するシステム

## 概要
KansyaConnectは、Slack上で簡単に感謝の気持ちを共有し、ポイントをやり取りすることができるアプリケーションです。チームメンバー間のポジティブなコミュニケーションを促進し、感謝の文化を育むことを目的としています。

## 主な機能
- Slack上でのポイント送信機能
- 日次ポイントリセット機能
- インタラクティブなメッセージ応答
- ワークスペース認証管理
- トランザクション履歴管理
- ユーザー情報管理

## システム構成
- サーバーレスアーキテクチャ（AWS Lambda + API Gateway）
- DynamoDBによるデータ管理
  - ユーザー情報テーブル
  - トランザクション履歴テーブル
  - 認証情報テーブル
- SNSによるイベント処理
- コンテナ化されたLambda関数

## デプロイ方法
1. AWS SAMを使用してデプロイ
2. 必要な環境変数をAWS Systems Managerのパラメータストアに設定
   - SLACK_BOT_TOKEN
   - SLACK_SIGNING_SECRET
   - SLACK_CLIENT_ID
   - SLACK_CLIENT_SECRET
   - SLACK_APP_ID

## APIエンドポイント
- イベント受信: `/slack/events`
- インタラクティブアクション: `/slack/interactive`
- OAuth認証: `/slack/oauth`