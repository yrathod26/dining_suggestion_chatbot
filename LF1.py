import json
import argparse
import pprint
import requests
import sys
import urllib
import datetime
import boto3
import logging
import os
import time

from boto3.dynamodb.conditions import Key, Attr
from botocore.exceptions import ClientError
from ast import literal_eval

logger = logging.getLogger()
logger.setLevel(logging.DEBUG)

def lambda_handler(event, context):
    
    os.environ['TZ'] = 'America/New_York'
    time.tzset()
    print(event)
    return type_event(event)


def type_event(event_intent):
    event_intent = event_intent['currentIntent']['name']
    print(' ')
    print(event_intent)
    
    # event type to your bot's intent handlers
    if event_intent == 'GreetingIntent':
        return greetingIntent(event_intent)
    elif event_intent == 'DiningSuggestionsIntent':
        return diningSuggestionIntent(event_intent)
    elif event_intent == 'ThankYouIntent':
        return thankYouIntent(event_intent)

    raise Exception('Intent ' + event_intent + ' not supported')
    
def greetingIntent(event_intent):

    #print("asdfghj")
    return {
        'dialogAction': {
            "type": "Close",
            "fulfillmentState": "Fulfilled",
            'message': {
                'contentType': 'PlainText', 
                'content': 'Hello, How can I help you?'}
        }
    }
    
def thankYouIntent(event_intent):
    return {
        'dialogAction': {
            "type": "Close",
            "fulfillmentState": "Fulfilled",
            'message': {
                'contentType': 'PlainText', 
                'content': 'Thank you for using our bot. It was my pleasure helping you.'}
        }
    }    


def diningSuggestionIntent(event_intent):
    
    location = getSlot(event_intent)["dslocation"]
    cuisine = getSlot(event_intent)["dscuisine"]
    noofpeople = getSlot(event_intent)["dsnoofpeople"]
    date = getSlot(event_intent)["dsdate"]
    time = getSlot(event_intent)["dstime"]
    phoneno = getSlot(event_intent)["dsphoneno"]
    source = event_intent['invocationSource']
    
    if source == 'DialogCodeHook':
        slots = getSlot(event_intent)
        
        validationResult = input_validation(location, cuisine, noofpeople, date, time, phoneno)
        
        if not validationResult['isValid']:
            slots[validationResult['violatedSlot']] = None
            
            return elicitSlot(event_intent['sessionAttributes'],
                               event_intent['currentIntent']['name'],
                               slots,
                               validationResult['violatedSlot'],
                               validationResult['message'])
                               
        outputSessionAttributes = event_intent['sessionAttributes'] if event_intent['sessionAttributes'] is not None else {}
        

        return delegate(outputSessionAttributes, getSlot(event_intent))
    
    if phoneno is not None : #After user enters phone number, Data is sent in SNS Queue.


        #print(cuisine)
        #print(phoneno)
        data = {
                        "term":cuisine,
                        "location":location,
                        "categories":cuisine,
                        "Phone_number": phoneno,
                        "peoplenum": noofpeople,
                        "Time": time,
                        "Dining_Date": date
                }
                    
        messageId = SQS_request_start(data)
    
    return {
        'dialogAction': {
            "type": "ElicitIntent",
            'message': {
                'contentType': 'PlainText', 
                'content': 'Just a minute. Your suggestions are on the way.'}
        }
    }    
    

    
def SQS_request_start(Data):
    sqs = boto3.client('sqs')
    queue_url = 'https://sqs.us-east-1.amazonaws.com/636938905002/restTestQueue'
    delaySeconds = 5
    #input all message attributes.
    messageAttributes = {
        'Term': {
            'DataType': 'String',
            'StringValue': Data['term']
        },
        'Location': {
            'DataType': 'String',
            'StringValue': Data['location']
        },
        'Categories': {
            'DataType': 'String',
            'StringValue': Data['categories']
        },
        "DiningTime": {
            'DataType': "String",
            'StringValue': Data['Time']
        },
        "Dining_Date": {
            'DataType': "String",
            'StringValue': Data['Dining_Date']
        },
        'PeopleNum': {
            'DataType': 'Number',
            'StringValue': Data['peoplenum']
        },
        'Phone_number': {
            'DataType': 'Number',
            'StringValue': Data['Phone_number']
        }
    }
    
    messageBody=('Recommendation for the food')
    
    #Send request to the queue.
    response = sqs.send_message(
        QueueUrl = queue_url,
        DelaySeconds = delaySeconds,
        MessageAttributes = messageAttributes,
        MessageBody = messageBody
        )
            
    #print ('send data to queue')
    
    # print(response['MessageId'])
    
    # return response['MessageId']

def getSlot(event_intent):
    return event_intent['currentIntent']['slots']    
    

def isValidDate(date):
    try:
        dateutil.parser.parse(date)
        return True
    except ValueError:
        return False

def formatReturnMessage(pIsValid, pFailedSlot, pMessage):
    if pMessage is None:
        return {
            "isValid": pIsValid,
            "violatedSlot": pFailedSlot
        }

    return {
        'isValid': pIsValid,
        'violatedSlot': pFailedSlot,
        'message': {'contentType': 'PlainText', 'content': pMessage}
    } 

def input_validation(location, cuisine, Nop, date, time, phoneNo):
    
    locations = ['new york', 'manhattan', 'brooklyn']
    if location is not None and location.lower() not in locations:
        return formatReturnMessage(False,
                                    'dslocation',
                                    'Sorry, we do not have services in ' + location + '. Please enter locations only in New York.')  

    cuisines = ['indian', 'korean','chinese', 'american','mexican']
    if cuisine is not None and cuisine.lower() not in cuisines:
        return formatReturnMessage(False,
                                    'dscuisine',
                                    'We don\'t have cuisines like ' + cuisine + '. Choose something else.')                                      

    if Nop is not None:
        Nop = int(Nop)
        if Nop > 50 or Nop < 0:
            return formatReturnMessage(False,
                                      'dsnoofpeople',
                                      'Sorry, there is sitting for only 1 - 50. Please enter valid number.')    

    if phoneNo is not None :

        if len(phoneNo)<= 11 :
             return formatReturnMessage(False, 'dsphoneno', 'Please enter phone number in following format - +cc-xxx-xxx-xxxx') 

        if (phoneNo[1:].isdigit() == False):
            return formatReturnMessage(False,
                                      'dsphoneno',
                                      'Please enter phone number in following format - +cc-xxx-xxx-xxxx')
                                       
    return formatReturnMessage(True, None, None)    
    
def elicitSlot(pSessionAttributes, pIntentName, pSlots, pSlotsToElicit, pMessage):
    return {
        'sessionAttributes': pSessionAttributes,
        'dialogAction': {
            'type': 'ElicitSlot',
            'intentName': pIntentName,
            'slots': pSlots,
            'slotToElicit': pSlotsToElicit,
            'message': pMessage
        }
    }

def delegate(pSessionAttributes, pSlots):
    return {
        'sessionAttributes': pSessionAttributes,
        'dialogAction': {
            'type': 'Delegate',
            'slots': pSlots
        }
    }