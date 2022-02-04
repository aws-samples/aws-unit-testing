# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

'''An example Lambda function using the context object. 
Source code adapted from https://docs.aws.amazon.com/lambda/latest/dg/python-context.html.
Reference the AWS Lambda developer guide for the full list of context functions/properties.
Disclaimer: this is only created to demonstrate unit testing'''
def lambda_handler(event, context):   
    arn = context.invoked_function_arn
    log_stream = context.log_stream_name
    log_group = context.log_group_name
    request_id = context.aws_request_id
    memory_limit = context.memory_limit_in_mb
    remaining_time = context.get_remaining_time_in_millis()
    print("Lambda function ARN:", arn)
    print("CloudWatch log stream name:", log_stream)
    print("CloudWatch log group name:",  log_group)
    print("Lambda Request ID:", request_id)
    print("Lambda function memory limits in MB:", memory_limit)
    print("Lambda time remaining in MS:", remaining_time)
    return arn, log_stream, log_group, request_id, memory_limit, remaining_time