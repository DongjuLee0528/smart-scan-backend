import json


def lambda_handler(event, context):
    print("Inbound scanner Lambda invoked")
    print(json.dumps({"event": event}, default=str))

    return {
        "statusCode": 200,
        "headers": {"Content-Type": "application/json"},
        "body": json.dumps(
            {
                "service": "inbound-scanner",
                "message": "Inbound scanner Lambda is running.",
            }
        ),
    }
