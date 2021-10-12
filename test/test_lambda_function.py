# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

import boto3
import pytest
import logging
import sys
import os
import pathlib
import uuid
import re
import json
import time
from datetime import date
from moto import mock_s3, mock_ssm
from importlib import import_module

# discover the src directory to import the file being tested
parent_dir = pathlib.Path(__file__).parent.resolve()
src_path = os.path.join(parent_dir, '..', 'src')
sys.path.append(src_path)

# setup logging to terminal
level = logging.DEBUG
logger = logging.getLogger(__name__)
logger.setLevel(level)
ch = logging.StreamHandler()
ch.setLevel(level)
logger.addHandler(ch)

# monkey patch for environment variables and functions
mp = pytest.MonkeyPatch()
bucket_name = 'test-bucket'
access_key = 's3-access-key'
secret_key = 's3-secret-key'
ENV_BUCKET_KEY = 'S3_BUCKET'
ENV_ACCESS_KEY = 'S3_ACCESS_PARAM'
ENV_SECRET_KEY = 'S3_SECRET_PARAM'
ENV_REGION_KEY = 'AWS_DEFAULT_REGION'

# do all setup before running all tests here
def setup_module(module):
    mp.setenv(ENV_BUCKET_KEY, bucket_name)
    mp.setenv(ENV_ACCESS_KEY, access_key)
    mp.setenv(ENV_SECRET_KEY, secret_key)
    mp.setenv(ENV_REGION_KEY, 'us-east-1')

# teardown after running all tests 
def teardown_module(module):
    mp.delenv(ENV_BUCKET_KEY)
    mp.delenv(ENV_ACCESS_KEY)
    mp.delenv(ENV_SECRET_KEY)
    mp.delenv(ENV_REGION_KEY)

# cleanup all objects and buckets
def s3_delete_all(s3_client, bucket_name):
    objects = s3_client.list_objects_v2(Bucket=bucket_name)
    if 'Contents' in objects:
        # must delete all objects before deleting bucket
        for object in objects['Contents']:
            s3_client.delete_object(Bucket=bucket_name, Key=object['Key'])
    boto3.resource('s3').Bucket(bucket_name).delete()

'''mock the environment before importing by using a fixture. otherwise 
import errors will occur. refer to pytest documentation to change the 
scope of the fixture'''
@pytest.fixture()
def mocked_lambda_function():
    yield import_module('lambda_function')

@pytest.fixture()
def s3_fixture():
    with mock_s3():
        # do all setup here
        logger.debug('Setup s3 bucket')
        s3_client = boto3.client('s3')
        s3_client.create_bucket(Bucket=bucket_name)
        yield s3_client
        # do all teardown here
        s3_delete_all(s3_client, bucket_name)

@pytest.fixture() 
def ssm_fixture():
    with mock_ssm():
        logger.debug('Setup ssm parameter store')
        ssm_client = boto3.client('ssm')
        secure_type = 'SecureString'
        ssm_client.put_parameter(
            Name=access_key,
            Description='access key for s3 bucket {}'.format(bucket_name),
            Value=str(uuid.uuid1()),    # generated value. do not hardcode
            Type=secure_type
        )
        ssm_client.put_parameter(
            Name=secret_key,
            Description='secret key for s3 bucket {}'.format(bucket_name),
            Value=str(uuid.uuid1()),    # generated value. do not hardcode
            Type=secure_type
        )
        yield ssm_client
        ssm_client.delete_parameters(Names=[access_key, secret_key])
        
class TestConstructFilePath:
    # import the mocked_lambda_function last because it depends on the other fixtures
    def test_empty_fn(self, s3_fixture, ssm_fixture, mocked_lambda_function):
        logger.debug('Testing empty file name')
        result = mocked_lambda_function.construct_file_path('')
        today = date.today().strftime('%Y/%m/%d')
        # regex for multiple characters for uuid wildcard
        expected = os.path.join(today, '.+', '')
        expected = re.compile(expected)
        match = bool(re.match(expected, result))
        logger.debug('Result: {}'.format(result))
        logger.debug('Expected: {}'.format(expected))
        assert match

    def test_path_constructed(self, s3_fixture, ssm_fixture, mocked_lambda_function):
        logger.debug('Testing file path constructed')
        file_name = 'my-file-name'
        result = mocked_lambda_function.construct_file_path(file_name)
        today = date.today().strftime('%Y/%m/%d')
        # regex for multiple characters for uuid wildcard
        expected = os.path.join(today, '.+', file_name)
        expected = re.compile(expected)
        match = bool(re.match(expected, result))
        logger.debug('Result: {}'.format(result))
        logger.debug('Expected: {}'.format(expected))
        assert match

class TestConstructJson:
    def test_count_not_in_body(self, s3_fixture, ssm_fixture, mocked_lambda_function):
        logger.debug('Testing count not in body')
        body = {}
        id = str(uuid.uuid1())
        result = mocked_lambda_function.construct_json(body, id)
        expected = json.dumps({
            'id': id,
            'count': 10
        })
        logger.debug('Result: {}'.format(result))
        logger.debug('Expected: {}'.format(expected))
        assert result == expected

    def test_count_int_in_body(self, s3_fixture, ssm_fixture, mocked_lambda_function):
        logger.debug('Testing count (int) in body')
        body = {'id': 'temp', 'count': 7}
        id = str(uuid.uuid1())
        result = mocked_lambda_function.construct_json(body, id)
        expected = json.dumps({
            'id': id,
            'count': 17
        })
        logger.debug('Result: {}'.format(result))
        logger.debug('Expected: {}'.format(expected))
        assert result == expected

    def test_count_double_in_body(self, s3_fixture, ssm_fixture, mocked_lambda_function):
        logger.debug('Testing count invalid type (double) in body')
        body = {'id': 'temp', 'count': 9.9}
        id = str(uuid.uuid1())
        result = mocked_lambda_function.construct_json(body, id)
        expected = json.dumps({
            'id': id,
            'count': 10
        })
        logger.debug('Result: {}'.format(result))
        logger.debug('Expected: {}'.format(expected))
        assert result == expected

    def test_count_str_in_body(self, s3_fixture, ssm_fixture, mocked_lambda_function):
        logger.debug('Testing count invalid type (str) in body')
        body = {'id': 'temp', 'count': ''}
        id = str(uuid.uuid1())
        result = mocked_lambda_function.construct_json(body, id)
        expected = json.dumps({
            'id': id,
            'count': 10
        })
        logger.debug('Result: {}'.format(result))
        logger.debug('Expected: {}'.format(expected))
        assert result == expected

class TestLambdaHandler:
    def verify_body_in_s3(self, s3_client, objects_list, expected_list):
        logger.debug('Verifying body for objects in s3')
        if len(objects_list) != len(expected_list):
            logger.error('expected_list not configured properly')
            assert len(objects_list) == len(expected_list)

        for i in range(len(objects_list)):
            object = s3_client.get_object(Bucket=bucket_name, Key=objects_list[i]['Key'])
            body = json.loads(object['Body'].read())
            expected = expected_list[i]
            assert 'id' in body
            del body['id']
            del expected['id']
            logger.debug('Result: {}'.format(body))
            logger.debug('Expected: {}'.format(expected))
            assert body == expected

    def test_no_files(self, s3_fixture, ssm_fixture, mocked_lambda_function):
        logger.debug('Testing no files passed in')
        event = {
            'files': []
        }
        context = {}

        result = json.loads(mocked_lambda_function.lambda_handler(event, context)['files'])
        expected = []
        logger.debug('Result: {}'.format(result))
        logger.debug('Expected: {}'.format(expected))
        assert result == expected

        result = 'Contents' in s3_fixture.list_objects_v2(Bucket=bucket_name)
        expected = False
        logger.debug('Testing s3 bucket is empty')
        logger.debug('Result: {}'.format(result))
        logger.debug('Expected: {}'.format(expected))
        assert result == expected        

    def test_one_file(self, s3_fixture, ssm_fixture, mocked_lambda_function):
        logger.debug('Testing one file passed in')
        body = {'creationTime': time.time(), 'description': 'test', 'success': True}
        event = {
            'files': [
                {'name': 'file-1', 'body': body}
            ]
        }
        context = {}
        result = json.loads(mocked_lambda_function.lambda_handler(event, context)['files'])
        expected = ['file-1']
        logger.debug('Result: {}'.format(result))
        logger.debug('Expected: {}'.format(expected))
        assert result == expected

        objects_list = s3_fixture.list_objects_v2(Bucket=bucket_name)
        assert 'Contents' in objects_list
        
        result = len(objects_list['Contents'])
        expected = 1
        logger.debug('Testing s3 bucket contains 1 object')
        logger.debug('Result: {}'.format(result))
        logger.debug('Expected: {}'.format(expected))
        assert result == expected

        body['count'] = 10
        expected_list = [body]
        self.verify_body_in_s3(s3_fixture, objects_list['Contents'], expected_list)
        
    def test_multiple_files(self, s3_fixture, ssm_fixture, mocked_lambda_function):
        logger.debug('Testing multiple files passed in')
        body1 = {'creationTime': time.time(), 'description': 'test', 'success': True}
        body2 = {'count': 20, 'creationTime': time.time(), 'description': 'dev', 'success': False}
        body3 = {'creationTime': time.time(), 'description': 'prod', 'success': True}
        event = {
            'files': [
                {'name': 'file-1', 'body': body1},
                {'name': 'file-2', 'body': body2},
                {'name': 'file-3', 'body': body3}
            ]
        }
        context = {}
        result = json.loads(mocked_lambda_function.lambda_handler(event, context)['files'])
        expected = ['file-1', 'file-2', 'file-3']
        logger.debug('Result: {}'.format(result))
        logger.debug('Expected: {}'.format(expected))
        assert result == expected

        objects_list = s3_fixture.list_objects_v2(Bucket=bucket_name)
        assert 'Contents' in objects_list
        
        result = len(objects_list['Contents'])
        expected = 3
        logger.debug('Testing s3 bucket contains 3 objects')
        logger.debug('Result: {}'.format(result))
        logger.debug('Expected: {}'.format(expected))
        assert result == expected

        body1['count'] = 10
        body2['count'] = 30
        body3['count'] = 10
        expected_list = [body1, body2, body3]
        self.verify_body_in_s3(s3_fixture, objects_list['Contents'], expected_list)

    def test_files_not_uploaded(self, s3_fixture, ssm_fixture, mocked_lambda_function):
        logger.debug('Testing multiple files passed in but not uploaded')
        event = {
            'files': [
                {'body': {'creationTime': time.time(), 'description': 'test', 'success': True}},
                {'count': 20, 'body': {'creationTime': time.time(), 'description': 'dev', 'success': False}},
                {'body': {'creationTime': time.time(), 'description': 'prod', 'success': True}}
            ]
        }
        context = {}
        result = json.loads(mocked_lambda_function.lambda_handler(event, context)['files'])
        expected = []
        logger.debug('Result: {}'.format(result))
        logger.debug('Expected: {}'.format(expected))
        assert result == expected

        result = 'Contents' in s3_fixture.list_objects_v2(Bucket=bucket_name)
        expected = False
        logger.debug('Testing s3 bucket empty')
        logger.debug('Result: {}'.format(result))
        logger.debug('Expected: {}'.format(expected))
        assert result == expected
 
    def test_files_some_not_uploaded(self, s3_fixture, ssm_fixture, mocked_lambda_function):
        logger.debug('Testing multiple files passed in but some not uploaded')
        body = {'creationTime': time.time(), 'description': 'dev', 'success': False}
        event = {
            'files': [
                {'count': 1, 'body': {'creationTime': time.time(), 'description': 'test', 'success': True}},
                {'name': 'file-2', 'body': body},
                {'body': {'creationTime': time.time(), 'description': 'prod', 'success': True}}
            ]
        }
        context = {}
        result = json.loads(mocked_lambda_function.lambda_handler(event, context)['files'])
        expected = ['file-2']
        logger.debug('Result: {}'.format(result))
        logger.debug('Expected: {}'.format(expected))
        assert result == expected

        objects_list = s3_fixture.list_objects_v2(Bucket=bucket_name)
        assert 'Contents' in objects_list
        
        result = len(objects_list['Contents'])
        expected = 1
        logger.debug('Testing s3 bucket has one object')
        logger.debug('Result: {}'.format(result))
        logger.debug('Expected: {}'.format(expected))
        assert result == expected

        body['count'] = 10
        expected_list = [body]
        self.verify_body_in_s3(s3_fixture, objects_list['Contents'], expected_list)