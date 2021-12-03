# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

'''An example lambda function that authenticates with s3, constructs s3 objects, 
and puts the objects in the bucket specified by the environment variable. 
Disclaimer: this is only created to demonstrate unit testing'''
import boto3
import os
import uuid
import json
from datetime import date

# initialize all connections outside the function handler according to best practices

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

# create path by date and uuid
def construct_file_path(file_name): 
    today = date.today().strftime('%Y/%m/%d')
    file_id = str(uuid.uuid1())
    return os.path.join(today, file_id, file_name)

# add id to json file and add 10 to the count key
def construct_json(body, file_id):
    body['id'] = file_id
    if 'count' in body and isinstance(body['count'], int):
        body['count'] = int(body['count']) + 10
    else:
        body['count'] = 10
    return json.dumps(body)

# parses and uploads a json file to s3
def lambda_handler(event, context):
    files_uploaded = [] 
    count_files_not_uploaded = 0
    files_list = event['files']

    for file in files_list:
        if 'name' in file:
            # create the s3 key
            file_name = file['name']
            key = construct_file_path(file_name)
            # get second to last in path
            file_id = os.path.split(os.path.split(key)[0])[1]

            # create the s3 body
            body = construct_json(file['body'], file_id).encode('utf-8')
            
            # put in s3
            s3_client.put_object(Bucket=BUCKET_NAME, Key=key, Body=body)
            files_uploaded.append(file_name)
        else:
            count_files_not_uploaded += 1
    
    print(f'{count_files_not_uploaded} files not uploaded')
    return {
        'files': json.dumps(files_uploaded)
    }
