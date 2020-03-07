import json
import boto3
import requests


def lambda_handler(event, context):
        
    # Create SQS client
    sqs = boto3.client('sqs')
    
    queue_url = 'https://sqs.us-east-1.amazonaws.com/636938905002/ruptest'
    
    # Receive message from SQS queue
    response = sqs.receive_message(
        QueueUrl=queue_url,
        AttributeNames=[
            'SentTimestamp'
        ],
        MaxNumberOfMessages=1,
        MessageAttributeNames=[
            'All'
        ],
        VisibilityTimeout=0,
        WaitTimeSeconds=0
    )
    
   
    print(event)
    print(event['Records'])
    print(event['Records'][0]['messageAttributes'])
    
    
    
    print(response)
    # message = response['Messages'][0]
    
    
    receipt_handle = event['Records'][0]['receiptHandle']
    # receipt_handle = message['ReceiptHandle']
    
    # Delete received message from queue
    sqs.delete_message(
        QueueUrl=queue_url,
        ReceiptHandle=receipt_handle
    )
    
    # print('Received and deleted message: %s' % message)
    
    msgAttrib = event['Records'][0]['messageAttributes']
    # msgAttrib = message['MessageAttributes']
    location = msgAttrib['Location']['stringValue']
    cuisine = msgAttrib['Cuisine']['stringValue']
    noofpeople = msgAttrib['NoOfPeople']['stringValue']
    dtime = msgAttrib['DTime']['stringValue']
    ddate = msgAttrib['DDate']['stringValue']
    phoneno = msgAttrib['PhoneNo']['stringValue']
    
    url = 'https://search-restaurants-ha76texqossjbdrwxznviolaim.us-east-1.es.amazonaws.com/restaurants/_doc/_search?q=' + cuisine
    esdata = requests.post(url)
    esdjson = esdata.json()
    
    count = 0
    dynamodb = boto3.resource('dynamodb', region_name='us-east-1', endpoint_url="https://dynamodb.us-east-1.amazonaws.com")
    table = dynamodb.Table('yelp-restaurant')
    
    restaus = ""
    for item in esdjson['hits']['hits']:
        if count == 3:
            break;
        # businessIds.append(item['_source']['id'])
        try:
            respda = table.get_item(
                Key={
                    'id': item['_source']['id']
                }
            )
        except ClientError as e:
            print(e.response['Error']['Message'])
        else:
            if 'Item' in respda:
                # print(respda['Item'])
                count = count + 1
                # print(respda['Item']['location'][0])
                restaus = restaus + str(count) + " : " + respda['Item']['name'] + " ,located at  "+respda['Item']['location'][0] + " " +respda['Item']['location'][1] + " "
        
    
    # print(restaus)
                
    
    # # Create an SNS client
    client = boto3.client("sns")
    sndmsg = 'Hello! Here are my ' + cuisine + ' restaurant suggestions for ' + str(noofpeople) + ' people, for ' + str(ddate) + ' at ' + str(dtime) +'.' + restaus + ' Enjoy your meal!'
    #sndmsg = 'hello Rupesh'
    
    # Send your sms message.
    client.publish(
        PhoneNumber= phoneno,
        Message=sndmsg
    )
    
    
class DecimalEncoder(json.JSONEncoder):
    def default(self, o):
        if isinstance(o, decimal.Decimal):
            if o % 1 > 0:
                return float(o)
            else:
                return int(o)
        return super(DecimalEncoder, self).default(o)

