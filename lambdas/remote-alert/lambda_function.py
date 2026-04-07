from services.remote_service import send_remote_alert


def lambda_handler(event, context):
    return send_remote_alert(event)
