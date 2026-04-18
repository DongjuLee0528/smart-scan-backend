"""
AWS Lambda handler for SmartScan FastAPI backend.

Uses Mangum adapter to translate API Gateway events into ASGI requests.
"""

from mangum import Mangum

from backend.app import app

# API Gateway (REST) + CloudFront behavior /api/* routes here.
# lifespan="off" because Lambda cold starts handle startup per-invocation.
handler = Mangum(app, lifespan="off", api_gateway_base_path="/")
