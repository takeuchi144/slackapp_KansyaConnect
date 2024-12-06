aws ssm delete-parameter --name "/KansyaConnect/slack-token"
aws ssm delete-parameter --name "/KansyaConnect/slack-signing-secret"
aws ssm delete-parameter --name "/KansyaConnect/slack-client-id"
aws ssm delete-parameter --name "/KansyaConnect/slack-client-secret"


aws ssm put-parameter --name "/KansyaConnect/slack-token" --value "xoxb-7863312168613-8036993086465-BJYTh57HheRf9msBn460OqJp" --type String --overwrite
aws ssm put-parameter --name "/KansyaConnect/slack-signing-secret" --value "95e20b868f7297487c44e4da4dd3b6af" --type String --overwrite
aws ssm put-parameter --name "/KansyaConnect/slack-client-id" --value "7863312168613.8038934709568" --type String --overwrite
aws ssm put-parameter --name "/KansyaConnect/slack-client-secret" --value "04b934e69c9c5d012f7f7a0b1553f02a" --type String --overwrite
