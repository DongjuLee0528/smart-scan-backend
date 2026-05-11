"""
Inbound Scan Processing Lambda Function

Lambda function that receives and processes scan data from Raspberry Pi RFID readers.
Called through API Gateway POST /inbound endpoint.

Key Features:
- RFID scan data validation and processing
- Missing item detection
- Automatic invocation of outbound-notifier Lambda for email alerts
- Scan log storage in Supabase

Trigger: API Gateway (POST /inbound)
Data Source: Raspberry Pi UHF RFID Reader
"""

from services.scan_service import process_scan


def lambda_handler(event, context):
    """
    Lambda entry point - Processes RFID scan data.

    Args:
        event: API Gateway event (containing RFID scan data)
        context: Lambda execution context

    Returns:
        HTTP response (statusCode, headers, body)
    """
    return process_scan(event)
