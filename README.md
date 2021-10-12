## Unit Testing Interactions with Amazon Web Services (AWS) 

Unit testing AWS interactions with pytest and moto. These examples demonstrate how to structure, setup, teardown, mock, and conduct unit testing. The source code is only intended to demonstrate unit testing.

## Python Modules Used

[boto3](https://pypi.org/project/boto3/): AWS Software Development Kit (SDK) 

[moto](https://pypi.org/project/moto/): mock AWS resources for testing

[pytest](https://pypi.org/project/pytest/): unit testing framework and monkey patching functions and environment variables

## Install Modules

`pip install -r requirements.txt`

## Directory Structure

Place all your unit tests in the test folder 

## Running pytest

Run all tests 

`cd test` 

`pytest`

Run only one test

`cd test` 

`pytest [filename]`

## Region

By default, the region needs to be us-east-1. The environment variables are already mocked for this in the test file. 

## Logging

These unit tests utilize Python's default logging class. Establish a common format to log your test cases to help debugging. 

## Structure

In the test folder, create one test file per module being tested.
In the test file, create one test class per function.
In each test class, create one function per test case. 

## Naming Convention for Files Containing Tests

For pytest to pick up your files, classes, and functions: 
- Name your test files starting with `test_` 
- Name your classes starting with `Test`
- Name your functions starting with `test`

Refer to the pytest documentation for more info.

## Security

See [CONTRIBUTING](CONTRIBUTING.md#security-issue-notifications) for more information.

## License

This library is licensed under the MIT-0 License. See the LICENSE file.

