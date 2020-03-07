import json
import pprint
from botocore.vendored import requests
import sys
import urllib
from datetime import datetime
import dateutil
import math
import boto3
import logging
import os
import time

logger = logging.getLogger()
logger.setLevel(logging.DEBUG)

def lambda_handler(event, context):
    
    os.environ['TZ'] = 'America/New_York'
    time.tzset()
    print(event)
    return dispatch(event)


def dispatch(intentRequest):
    intentName = intentRequest['currentIntent']['name']
    
    # Dispatch to your bot's intent handlers
    if intentName == 'GreetingIntent':
        return greetingIntent(intentRequest)
    elif intentName == 'DiningSuggestionsIntent':
        return diningSuggestionIntent(intentRequest)
    elif intentName == 'ThankYouIntent':
        return thankYouIntent(intentRequest)

    raise Exception('Intent ' + intentName + ' not supported')
    
def greetingIntent(intentRequest):
    return {
        'dialogAction': {
            "type": "Close",
            "fulfillmentState": "Fulfilled",
            'message': {
                'contentType': 'PlainText', 
                'content': 'Hi there, how can I help?'}
        }
    }
    
def thankYouIntent(intentRequest):
    return {
        'dialogAction': {
            "type": "Close",
            "fulfillmentState": "Fulfilled",
            'message': {
                'contentType': 'PlainText', 
                'content': 'Thank you for using our service. It was pleasure helping you.'}
        }
    }    


def diningSuggestionIntent(intentRequest):
    
    location = getSlot(intentRequest)["dslocation"]
    cuisine = getSlot(intentRequest)["dscuisine"]
    noofpeople = getSlot(intentRequest)["dsnoofpeople"]
    date = getSlot(intentRequest)["dsdate"]
    time = getSlot(intentRequest)["dstime"]
    phoneno = getSlot(intentRequest)["dsphoneno"]
    source = intentRequest['invocationSource']
    
    if source == 'DialogCodeHook':
        slots = getSlot(intentRequest)
        
        validationResult = validateUInputs(location, cuisine, noofpeople, date, time, phoneno)
        
        if not validationResult['isValid']:
            slots[validationResult['violatedSlot']] = None
            
            return elicitSlot(intentRequest['sessionAttributes'],
                               intentRequest['currentIntent']['name'],
                               slots,
                               validationResult['violatedSlot'],
                               validationResult['message'])
                               
        outputSessionAttributes = intentRequest['sessionAttributes'] if intentRequest['sessionAttributes'] is not None else {}
        
        return delegate(outputSessionAttributes, getSlot(intentRequest))
    
    UData = {
                    "location":location,
                    "cuisine":cuisine,
                    "noofpeople":noofpeople,
                    "ddate": date,
                    "dtime": time,
                    "phoneno": phoneno,
            }
                
    messageId = reqResSQS(UData)
    
    return {
        'dialogAction': {
            "type": "ElicitIntent",
            'message': {
                'contentType': 'PlainText', 
                'content': 'You’re all set. Expect my suggestions shortly! Have a good day.'}
        }
    }    
    
def getSlot(intentRequest):
    return intentRequest['currentIntent']['slots']    
    

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

def validateUInputs(pLocation, pCuisine, pNoOfPeople, pDinningDate, pDinningTime, pPhoneNo):
    
    locations = ['new york', 'manhattan', 'brooklyn']
    if pLocation is not None and pLocation.lower() not in locations:
        return formatReturnMessage(False,
                                    'dslocation',
                                    'Sorry, our services are yet to reach in ' + pLocation + '. Please enter locations in New York.')  

    cuisines = ['indian', 'italian', 'french','chinese', 'american']
    if pCuisine is not None and pCuisine.lower() not in cuisines:
        return formatReturnMessage(False,
                                    'dscuisine',
                                    'We don\'t offer cuisines like ' + pCuisine + '. Pick something else.')                                      

    if pNoOfPeople is not None:
        pNoOfPeople = int(pNoOfPeople)
        if pNoOfPeople > 50 or pNoOfPeople < 0:
            return formatReturnMessage(False,
                                      'dsnoofpeople',
                                      'Sorry, Restaurants offer ony 1 to 50 people seatings at a time. Please enter valid number.')    

    currdate = str(datetime.now()).split()
    
    if pDinningDate is not None:
        if not isValidDate(pDinningDate):
            return formatReturnMessage(False, 'dsdate', 'I did not understand the date format you used.Please use a valid date format.')
        if currdate[0] > str(pDinningDate):
            return formatReturnMessage(False, 'dsdate', 'Even I would love to time travel in the past. But can\'t.So Please enter date from today onwards.')   


    if pDinningTime is not None:

        if len(pDinningTime) != 5:
            return formatReturnMessage(False, 'dstime', 'Please enter time in correct format - HH:MM')
    
        hour, minute = pDinningTime.split(':')
        hour = int(hour)
        minute = int(minute)
    
        if math.isnan(hour) or math.isnan(minute):
            return formatReturnMessage(False, 'dstime', 'Please enter time in correct format - HH:MM')
    
        if (hour < 8 or hour > 24) :
            return formatReturnMessage(False, 'dstime', 'Our business hours are from 8 am to midnight. Can you specify a time during this range?')
        
        if (currdate[0] == str(pDinningDate) and (currdate[1] > str(pDinningTime) )):
            return formatReturnMessage(False, 'dstime', 'You are late. Please select another time. ')

    if pPhoneNo is not None :

        if len(pPhoneNo)<= 11 :
             return formatReturnMessage(False, 'dsphoneno', 'Please enter correct phone number with country code - +cc-xxx-xxx-xxxx') 

        if (pPhoneNo[1:].isdigit() == False):
            return formatReturnMessage(False,
                                      'dsphoneno',
                                      'Please enter correct phone number.Don\'t worry we wont spam you.')
                                       
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



def reqResSQS(pData):
    sqs = boto3.client('sqs')
    queue_url = '	https://sqs.us-east-1.amazonaws.com/636938905002/ruptest'
    delaySeconds = 5
    messageAttributes = {
        'Location': {
            'DataType': 'String',
            'StringValue': pData['location']
        },
        'Cuisine': {
            'DataType': 'String',
            'StringValue': pData['cuisine']
        },
        'NoOfPeople': {
            'DataType': 'String',
            'StringValue': pData['noofpeople']
        },
        "DDate": {
            'DataType': "String",
            'StringValue': pData['ddate']
        },
        "DTime": {
            'DataType': "String",
            'StringValue': pData['dtime']
        },
        'PhoneNo': {
            'DataType': 'String',
            'StringValue': pData['phoneno']
        },
    }
    
    messageBody=('Recommendation for restaurants')
    
    response = sqs.send_message(
        QueueUrl = queue_url,
        DelaySeconds = delaySeconds,
        MessageAttributes = messageAttributes,
        MessageBody = messageBody
        )

    return response['MessageId']
