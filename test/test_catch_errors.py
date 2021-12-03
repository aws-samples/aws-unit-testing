# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

import boto3
import pytest
import logging
import sys
import os
import pathlib
import uuid
import json
from unittest import mock
from moto import mock_s3, mock_ssm
from importlib import import_module

module_name = 'catch_errors'

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
    response = s3_client.list_objects_v2(Bucket=bucket_name)
    if 'Contents' in response:
        # must delete all objects before deleting bucket
        for o in response['Contents']:
            s3_client.delete_object(Bucket=bucket_name, Key=o['Key'])
    boto3.resource('s3').Bucket(bucket_name).delete()

'''Mock the AWS services and environment variables before importing the module. 
Use a fixture to control the import. Otherwise import errors will occur. refer 
to the pytest documentation to change the scope of the fixture'''
@pytest.fixture()
def catch_errors_module():
    yield import_module(module_name)

@pytest.fixture()
def s3_fixture():
    with mock_s3():
        # do all setup here
        logger.debug('Setup s3 bucket')
        s3_client = boto3.client('s3')
        s3_client.create_bucket(Bucket=bucket_name)
        # pass the client to the test case
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

class TestMyPutObject:
    # import the catch_errors_module last because it depends on the other fixtures
    def test_put_success(self, s3_fixture, ssm_fixture, catch_errors_module):
        logger.debug('Testing object successfully put in s3')
        expected = {'key': 'test_put_success'}
        key = str(uuid.uuid1())
        body = json.dumps(expected)
        # call to test function
        catch_errors_module.my_put_object(key, body)
        # check the object was put successfully
        response = s3_fixture.get_object(Bucket=bucket_name, Key=key)
        result = json.loads(response['Body'].read())
        logger.debug('Result: {}'.format(result))
        logger.debug('Expected: {}'.format(expected))
        assert result == expected

    def test_put_error(self, s3_fixture, ssm_fixture, catch_errors_module):
        logger.debug('Testing exception RAISED (mock put_object to raise an exception)')
        key = str(uuid.uuid1())
        body = json.dumps({})
        expected = '[TEST] exception message for test_put_error'
        # get the raised exception
        with pytest.raises(Exception) as execinfo:
            # mock the boto3 put_object to raise an exception
            with mock.patch(module_name + '.s3_client.put_object', side_effect=Exception(expected)):
                catch_errors_module.my_put_object(key, body)
        # get the raised exception message back
        result = execinfo.value.args[0]
        logger.debug('Result: {}'.format(result))
        logger.debug('Expected: {}'.format(expected))
        # check the mocked exception message was received
        assert result == expected

class TestMyGetObject:
    def test_get_success(self, s3_fixture, ssm_fixture, catch_errors_module):
        logger.debug('Testing object successfully retrieved from s3')
        expected = {'key': 'test_get_success'}
        # setup the object in s3 
        key = str(uuid.uuid1())
        body = json.dumps(expected).encode('utf-8')
        s3_fixture.put_object(Bucket=bucket_name, Key=key, Body=body)
        # call the test function
        result = catch_errors_module.my_get_object(key)
        # check the object was retrieved  successfully
        logger.debug('Result: {}'.format(result))
        logger.debug('Expected: {}'.format(expected))
        assert result == expected

    def test_get_error(self, s3_fixture, ssm_fixture, catch_errors_module):
        logger.debug('Testing exception CAUGHT (mock get_object to raise an exception)')
        key = str(uuid.uuid1())
        # mock the boto3 get_object() function to raise an exception
        with mock.patch(module_name + '.s3_client.get_object', side_effect=Exception('[TEST] exception message for test_get_error')):
            result = catch_errors_module.my_get_object(key)
        expected = False
        logger.debug('Result: {}'.format(result))
        logger.debug('Expected: {}'.format(expected))
        # check the exception was caught. my_get_object() returns false after catching the exception.
        assert result == expected

    def test_get_error(self, s3_fixture, ssm_fixture, catch_errors_module):
        logger.debug('Testing mocked get_object returns none')
        key = str(uuid.uuid1())
        # create function to replace get_object()  (parameters are required)
        def mock_get_object_return(Bucket, Key):
            return None     # response=None will cause response['Body'] to fail in my_get_object()
        # mock the boto3 get_object() to be mock_get_object_return()
        mp.setattr(catch_errors_module.s3_client, 'get_object', mock_get_object_return)
        # now whenever get_object() is called, mock_get_object_return() is actually called instead
        result = catch_errors_module.my_get_object(key)
        expected = False
        logger.debug('Result: {}'.format(result))
        logger.debug('Expected: {}'.format(expected))
        # check the exception was caught. my_get_object() returns false after catching the exception.
        assert result == expected

class TestMyListObjectsV2:
    def test_list_success(self, s3_fixture, ssm_fixture, catch_errors_module):
        logger.debug('Testing objects from s3 successfully listed')
        # setup the object in s3 
        key = str(uuid.uuid1())
        body = json.dumps({'key': 'test_get_success'}).encode('utf-8')
        s3_fixture.put_object(Bucket=bucket_name, Key=key, Body=body)
        # call to test function
        result = catch_errors_module.my_list_objects_v2()
        assert len(result) == 1 # there should only be 1 object
        result = result[0]['Key']
        expected = key
        logger.debug('Result: {}'.format(result))
        logger.debug('Expected: {}'.format(expected))
        assert result == expected

    def test_list_error(self, s3_fixture, ssm_fixture, catch_errors_module):
        logger.debug('Testing exception CAUGHT (mock list_objects_v2 to raise an exception)')
        # mock the boto3 list_objects_v2 to raise an exception
        with mock.patch(module_name + '.s3_client.list_objects_v2', side_effect=Exception('[TEST] exception message for test_list_error')):
            result = catch_errors_module.my_list_objects_v2()
        expected = False
        logger.debug('Result: {}'.format(result))
        logger.debug('Expected: {}'.format(expected))
        assert result == expected

    def test_list_no_contents(self, s3_fixture, ssm_fixture, catch_errors_module):
        logger.debug('Testing exception RAISED when no contents in bucket')
        # call the function inside the block to get the raised exception
        with pytest.raises(Exception) as execinfo:
            catch_errors_module.my_list_objects_v2()
        # get the exception message back
        result = execinfo.value.args[0]
        expected = 'Bucket empty'
        logger.debug('Result: {}'.format(result))
        logger.debug('Expected: {}'.format(expected))
        # check an exception was raised
        assert result == expected
