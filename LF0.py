import json
import boto3

client = boto3.client('lex-runtime')

def lambda_handler(event, context):
    print(event)
    response = client.post_text(
        botName='RestRecBot',
        botAlias='$LATEST',
        userId='admin',
        inputText=event["message"])
    inputText=event["message"]
    return {
        'statusCode': 200,
        'body': response
    }