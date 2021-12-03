# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

'''An example of handling errors with s3 functions. 
Disclaimer: this is only created to demonstrate unit testing'''
import boto3
import os 
import json

# configure aws authentication
BUCKET_NAME = os.environ['S3_BUCKET']
SSM_S3_ACCESS_PARAM = os.environ['S3_ACCESS_PARAM']
SSM_S3_SECRET_PARAM = os.environ['S3_SECRET_PARAM']

# get s3 credentials from ssm
ssm_client = boto3.client('ssm')
ACCESS_KEY = ssm_client.get_parameter(Name=SSM_S3_ACCESS_PARAM, WithDecryption=True)['Parameter']['Value']
SECRET_KEY = ssm_client.get_parameter(Name=SSM_S3_SECRET_PARAM, WithDecryption=True)['Parameter']['Value']

# NOTE: do not hardcode these values
s3_client = boto3.client('s3', aws_access_key_id=ACCESS_KEY, aws_secret_access_key=SECRET_KEY)

def my_put_object(key, body):
    # encodes the body and puts it in the bucket
    body = body.encode('utf-8')
    s3_client.put_object(Bucket=BUCKET_NAME, Key=key, Body=body)

def my_get_object(key):
    # return body of object in s3. return false if exception raised.
    try: 
        response = s3_client.get_object(Bucket=BUCKET_NAME, Key=key)
        body = json.loads(response['Body'].read())
    except Exception as e:
        print(e)
        return False
    return body

def my_list_objects_v2():
    # return list of objects in s3. return false if exception raised. 
    try: 
        response = s3_client.list_objects_v2(Bucket=BUCKET_NAME)
    except Exception as e:
        print(e)
        return False

    # if there is nothing in the bucket, raise an exception
    if 'Contents' not in response:
        raise Exception('Bucket empty')

    return response['Contents']
