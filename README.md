# FinnGen Endpoint tools

Collection of tools to help working on the FinnGen endpoints.


## **Endpoint Definition Checker**

Validates the endpoint definition file against several checks.


### How to run

1. Install [uv](https://docs.astral.sh/uv/), the python project manager.
2. Run `uv run flask --app fg_endpoint_tools.server run`


### How to make changes

The different checks are implemented in the file [definition_checker.py](src/fg_endpoint_tools/definition_checker.py). You can change an existing check or add a new one there.

It's also good to look at the [test_definition_checker.py](tests/test_definition_checker.py) code to understand how the implementation works.

The user interface code is located in [src/fg_endpoint_tools/templates](src/fg_endpoint_tools/templates).
