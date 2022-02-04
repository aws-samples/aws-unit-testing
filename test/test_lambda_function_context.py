# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

'''Lambda functions often use the provided context object that provide 
information about the invocation, function, and execution environment. 
The context object, which is normally passed into the lambda function by 
default, needs to be mocked when testing lambda functions.
NOTE: You only need to mock the context object for testing if it is called 
inside your Lambda function'''

import pytest
import logging
import sys
import os
import pathlib
import uuid
from unittest.mock import patch
# discover the src directory to import the file being tested
parent_dir = pathlib.Path(__file__).parent.resolve()
src_path = os.path.join(parent_dir, '..', 'src')
sys.path.append(src_path)
from lambda_function_context import lambda_handler

# setup logging to terminal
level = logging.DEBUG
logger = logging.getLogger(__name__)
logger.setLevel(level)
ch = logging.StreamHandler()
ch.setLevel(level)
logger.addHandler(ch)

# an empty class to mock
class context:
    pass

# demonstrate mocking lambda context methods/properties for unit testing
class TestLambdaHandler:
    # normally, calling the lambda function that uses the context object locally will result in an error
    def test_lambda_handler_context_error(self):
        logger.debug('Demonstrating calling lambda function without mocking the context object will result in an error')
        with pytest.raises(Exception) as execinfo:
            lambda_handler({}, context())
        # get the raised exception message back
        result = execinfo.value.args[0]
        expected = '\'context\' object has no attribute'
        logger.debug('Result: {}'.format(result))
        logger.debug('Expected: {}'.format(expected))
        # check the mocked exception message was received
        assert expected in result

    '''Mock the context object to test the lambda function locally. Context functions/properties are not 
    limited to what is shown below. Reference the AWS Lambda developer guide for the full list of 
    context methods/properties.'''
    def test_invoked_function_arn(self):
        logger.debug('Testing ability to mock lambda context object')
        # set the return values to mock
        arn = 'arn:aws:lambda:us-east-1:accountid:function:context'
        log_stream = 'date[$LATEST]id'
        log_group = '/aws/lambda/context'
        request_id = str(uuid.uuid1())
        memory_limit = 128
        remaining_time = 2999
        # mock the context object and set its attributes
        with patch('test_lambda_function_context.context') as mock_context:
            instance = mock_context.return_value
            # instance variables
            instance.invoked_function_arn = arn
            instance.log_stream_name = log_stream
            instance.log_group_name = log_group
            instance.aws_request_id = request_id
            instance.memory_limit_in_mb = memory_limit
            # instance functions: use .return_value for functions
            instance.get_remaining_time_in_millis.return_value = remaining_time
            result = lambda_handler({}, context())
        # check the mocked values were returned
        expected = (arn, log_stream, log_group, request_id, memory_limit, remaining_time)
        logger.debug('Result: {}'.format(result))
        logger.debug('Expected: {}'.format(expected))
        assert result == expected
