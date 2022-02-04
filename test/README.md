## Testing Guide

A quick guide for what each test example contains.

## [test_catch_errors.py](test_catch_errors.py)

- Importing the module to be tested as a pytest fixture.
- Setting up and tearing down test elements.
- Structuring test classes and cases.
- Mocking environment variables and some AWS services.
- Test for a raised exception

    ```
    # call the function inside the block to get the raised exception
    with pytest.raises(Exception) as execinfo:
        function_call()
    # get the exception message back
    result = execinfo.value.args[0]
    expected = 'Exception message here'
    # verify the exception thrown is what you expect
    assert result == expected
    ```

- Mocking functions to raise an exception

    ```
    with mock.patch('reference_to_function_to_mock', side_effect=Exception('Exception message here')):
        result = function_call()
    ```

- Mocking functions to return a custom output

    ```
    # create function to replace get_object()  (used parameters are required)
    def mock_get_object_return(Bucket, Key):
        return None     
    # set the boto3 get_object() to be mock_get_object_return()
    mp.setattr(catch_errors_module.s3_client, 'get_object', mock_get_object_return)
    # now whenever get_object() is called, mock_get_object_return() is actually called instead
    ```

## [test_lambda_function.py](test_lambda_function.py)

- Importing the module to be tested as a pytest fixture.
- Setting up and tearing down test elements.
- Structuring test classes and cases.
- Mocking environment variables and some AWS services.
- Testing logic for lambda_handler and helper functions.

## [test_lambda_function_context.py](test_lambda_function_context.py)

- Mocking Lambda context properties and methods.
- For the full list of context properties and methods, visit [https://docs.aws.amazon.com/lambda/latest/dg/python-context.html](https://docs.aws.amazon.com/lambda/latest/dg/python-context.html)
