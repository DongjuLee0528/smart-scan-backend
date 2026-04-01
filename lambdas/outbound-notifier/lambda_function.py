import json


def lambda_handler(event, context):
    print("Outbound notifier Lambda invoked")
    print(json.dumps({"event": event}, default=str))

    return {
        "statusCode": 200,
        "headers": {"Content-Type": "application/json"},
        "body": json.dumps(
            {
                "service": "outbound-notifier",
                "message": "Outbound notifier Lambda is running.",
            }
        ),
    }
