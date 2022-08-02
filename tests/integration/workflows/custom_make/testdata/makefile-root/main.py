import requests


def lambda_handler(event, context):
    # Just return the requests version.
    return f"{requests.__version__}"
