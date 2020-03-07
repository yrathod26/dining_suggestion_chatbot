import json
import argparse
import pprint
import requests
import sys
import urllib
import datetime
import boto3

from boto3.dynamodb.conditions import Key, Attr
from botocore.exceptions import ClientError
from ast import literal_eval

def lambda_handler(event, context):
    
	# Configuration for recieving message from SQS queue
    sqs = boto3.client('sqs')

	#URL
    queue = 'https://sqs.us-east-1.amazonaws.com/636938905002/restTestQueue/'
    
    response = sqs.receive_message(
        QueueUrl=queue,
        AttributeNames=[
            'All'
        ],
        MaxNumberOfMessages=1,
        MessageAttributeNames=[
            'All'
        ]
    )
    
	#Checking if 
    if('Messages' not in response):
        iterate = 0
    else:
        iterate = len(response['Messages'])
    
    for i in range(iterate):
        message = response['Messages'][i]
        receipt_handle = message['ReceiptHandle']

        # # Deletes messages from queue after it is read by LF2
        del_response = sqs.delete_message(
            QueueUrl=queue,
            ReceiptHandle=receipt_handle
        )
 
        location = message['Location']['StringValue']
        cuisine = message['Categories']['StringValue']
        phoneNumber = message['Phone_number']['StringValue']
        
        ids = []
        #cuisine = 'indian'
        url = 'https://search-restaurants-f3m3ryeapquwtywsuglhk7uvgu.us-east-1.es.amazonaws.com/restaurants/Restaurant/_search?q=' + cuisine
        req = requests.post(url).json()
    
    
    
        for items in req['hits']['hits']:
            dynamodb = boto3.resource('dynamodb', region_name='us-east-1')
            table = dynamodb.Table('yelp-restaurants')
            ids.append(items['_source']['RestaurantID'])
        
        output = fetchDataDynamoDB(table,  ids)
        print(output)
        
		#Configuration for connecting and sending message via SNS
        sns_client = boto3.client('sns')
        sns_client.publish(
             PhoneNumber=phoneNumber,
           Message="Hi,you restaurants for "+cuisine+" are as follows: "+ output
         )
        
        
    return {
            'statusCode': 200,
            'body': json.dumps('Hello from Lambda2!')
        }

   
def fetchDataDynamoDB(table,ids):
	if len(ids) <= 0:
			return 'Couldn't find any result.'
		op = ""
		count = 1
		print(ids)
		for i in range(3):
			try:
				response = table.get_item(
					Key={
						'id': ids[i]
					}
				)
			except ClientError as e:
				print(e.response['Error']['Message'])
			else:
				print("GetItem succeeded:")
			print('returnsed')
			if len(response['Item']) >= 1 :
				responseData1 = response['Item']
				str1 = ""
				for i in responseData1['location']:
					str1+=i+" "
				op = op + " " + str(count) + "." + responseData1['name'] + ", Location: " + str1
				count += 1
			
		op = op + " Enjoy!"
		return op
