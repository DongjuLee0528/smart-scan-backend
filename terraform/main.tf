terraform {
  required_version = ">= 1.5.0"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

# ==========================================
# Variables (sensitive information separated)
# Enter values in terraform.tfvars file for production
# Make sure to add terraform.tfvars to .gitignore!
# ==========================================

# [MODIFIED] Removed db_password, kakao_token → Replaced with Supabase variables
variable "supabase_url" {
  description = "Supabase project URL"
  type        = string
}

variable "supabase_service_key" {
  description = "Supabase Service Role Key (server-side only)"
  type        = string
  sensitive   = true
}

variable "resend_api_key" {
  description = "Resend email API Key"
  type        = string
  sensitive   = true
}

variable "acm_cert_arn" {
  description = "ACM certificate ARN for CloudFront (must be issued in us-east-1 region)"
  type        = string
}

# [MODIFIED] github_repo default value: smart-scan-backend → smart-scan
variable "github_repo" {
  description = "GitHub repository path (owner/repo format)"
  type        = string
  default     = "DongjuLee0528/smart-scan"
}

# ==========================================
# 1. Provider and basic VPC setup
# ==========================================
data "aws_caller_identity" "current" {}

provider "aws" {
  region = "ap-northeast-2"
}

# [REMOVED] VPC/Subnet/IGW/RoutingTable/SG → Removed orphaned resources as Lambda vpc_config is unused
# [REMOVED] rds_sg, lambda_to_rds, rds_from_lambda → Removed as RDS is not used

# ==========================================
# 5. IAM Role (Lambda Execution Role)
# ==========================================
# IAM policy document allowing Lambda service to assume this role
data "aws_iam_policy_document" "lambda_assume_role" {
  statement {
    actions = ["sts:AssumeRole"]
    principals {
      type        = "Service"
      identifiers = ["lambda.amazonaws.com"]
    }
  }
}

# IAM role for all Lambda functions with basic execution permissions
resource "aws_iam_role" "lambda_role" {
  name               = "smartscan-lambda-role"
  assume_role_policy = data.aws_iam_policy_document.lambda_assume_role.json
}

# Attach basic CloudWatch logs permission to Lambda role
resource "aws_iam_role_policy_attachment" "lambda_logs" {
  role       = aws_iam_role.lambda_role.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}

# [REMOVED] lambda_vpc_access → Removed as VPC is not used

# [MODIFIED] Removed EventBridge policy → Replaced with direct Lambda invocation policy for Inbound→Outbound/Remote
# Policy allowing Inbound Lambda to invoke Outbound and Remote Lambdas directly
resource "aws_iam_role_policy" "lambda_invoke_policy" {
  name   = "lambda-invoke-outbound-remote"
  role   = aws_iam_role.lambda_role.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect   = "Allow"
        Action   = ["lambda:InvokeFunction"]
        Resource = [
          aws_lambda_function.outbound.arn,
          aws_lambda_function.remote.arn
        ]
      }
    ]
  })
}

# ==========================================
# 7. Lambda Functions
# ==========================================
# Dummy deployment package for initial Lambda creation (GitHub Actions will deploy actual code)
data "archive_file" "dummy_lambda" {
  type        = "zip"
  output_path = "${path.module}/dummy_payload.zip"
  source {
    content  = "def lambda_handler(event, context): return {'statusCode': 200, 'body': 'Init'}"
    filename = "lambda_function.py"
  }
}

# [MODIFIED] Inbound Lambda: Removed VPC (Supabase public), changed environment variables to Supabase
# Lambda function for processing RFID scans from Raspberry Pi
resource "aws_lambda_function" "inbound" {
  function_name    = "smartscan-inbound"
  role             = aws_iam_role.lambda_role.arn
  handler          = "lambda_function.lambda_handler"
  runtime          = "python3.12"
  timeout          = 30
  filename         = data.archive_file.dummy_lambda.output_path
  source_code_hash = data.archive_file.dummy_lambda.output_base64sha256
  reserved_concurrent_executions = 5

  # [MODIFIED] Removed vpc_config (Supabase public endpoint, NAT not needed)

  environment {
    variables = {
      SUPABASE_URL         = var.supabase_url
      SUPABASE_SERVICE_KEY = var.supabase_service_key
    }
  }

  lifecycle {
    ignore_changes = [filename, source_code_hash]  # GitHub Actions deploys code
  }
}

# [MODIFIED] Outbound Lambda: Changed environment variables to Supabase + Resend (removed Kakao)
# Lambda function for sending email notifications when items go missing
resource "aws_lambda_function" "outbound" {
  function_name    = "smartscan-outbound"
  role             = aws_iam_role.lambda_role.arn
  handler          = "lambda_function.lambda_handler"
  runtime          = "python3.12"
  timeout          = 15
  filename         = data.archive_file.dummy_lambda.output_path
  source_code_hash = data.archive_file.dummy_lambda.output_base64sha256
  reserved_concurrent_executions = 5

  environment {
    variables = {
      SUPABASE_URL         = var.supabase_url
      SUPABASE_SERVICE_KEY = var.supabase_service_key
      RESEND_API_KEY       = var.resend_api_key
    }
  }

  lifecycle {
    ignore_changes = [filename, source_code_hash]
  }
}

# [ADDED] Lambda function for handling remote alert requests from web interface
resource "aws_lambda_function" "remote" {
  function_name    = "smartscan-remote"
  role             = aws_iam_role.lambda_role.arn
  handler          = "lambda_function.lambda_handler"
  runtime          = "python3.12"
  timeout          = 15
  filename         = data.archive_file.dummy_lambda.output_path
  source_code_hash = data.archive_file.dummy_lambda.output_base64sha256
  reserved_concurrent_executions = 5

  environment {
    variables = {
      SUPABASE_URL         = var.supabase_url
      SUPABASE_SERVICE_KEY = var.supabase_service_key
      RESEND_API_KEY       = var.resend_api_key
    }
  }

  lifecycle {
    ignore_changes = [filename, source_code_hash]
  }
}

# [ADDED] Lambda function for Kakao chatbot skill server integration
resource "aws_lambda_function" "chatbot" {
  function_name    = "smartscan-chatbot"
  role             = aws_iam_role.lambda_role.arn
  handler          = "lambda_function.lambda_handler"
  runtime          = "python3.12"
  timeout          = 15
  filename         = data.archive_file.dummy_lambda.output_path
  source_code_hash = data.archive_file.dummy_lambda.output_base64sha256
  reserved_concurrent_executions = 5

  environment {
    variables = {
      SUPABASE_URL         = var.supabase_url
      SUPABASE_SERVICE_KEY = var.supabase_service_key
    }
  }

  lifecycle {
    ignore_changes = [filename, source_code_hash]
  }
}

# [REMOVED] All EventBridge related resources removed
# - aws_cloudwatch_event_rule.missing_item_rule
# - aws_cloudwatch_event_target.trigger_outbound_lambda
# - aws_lambda_permission.allow_eventbridge
# Changed to direct Lambda invocation from Inbound Lambda to Outbound Lambda

# ==========================================
# 8. API Gateway
# ==========================================
# REST API Gateway for SmartScan backend services
resource "aws_api_gateway_rest_api" "api" {
  name = "SmartScan-API"
}

# POST /inbound — Receive RFID scan from Raspberry Pi
resource "aws_api_gateway_resource" "inbound" {
  rest_api_id = aws_api_gateway_rest_api.api.id
  parent_id   = aws_api_gateway_rest_api.api.root_resource_id
  path_part   = "inbound"
}

resource "aws_api_gateway_method" "inbound_post" {
  rest_api_id   = aws_api_gateway_rest_api.api.id
  resource_id   = aws_api_gateway_resource.inbound.id
  http_method   = "POST"
  authorization = "NONE"
}

resource "aws_api_gateway_integration" "inbound_lambda" {
  rest_api_id             = aws_api_gateway_rest_api.api.id
  resource_id             = aws_api_gateway_resource.inbound.id
  http_method             = aws_api_gateway_method.inbound_post.http_method
  integration_http_method = "POST"
  type                    = "AWS_PROXY"
  uri                     = aws_lambda_function.inbound.invoke_arn
}

resource "aws_lambda_permission" "allow_apigw_inbound" {
  statement_id  = "AllowAPIGatewayInvokeInbound"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.inbound.function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${aws_api_gateway_rest_api.api.execution_arn}/*/*"
}

# POST /chatbot — Kakao chatbot skill server
resource "aws_api_gateway_resource" "chatbot" {
  rest_api_id = aws_api_gateway_rest_api.api.id
  parent_id   = aws_api_gateway_rest_api.api.root_resource_id
  path_part   = "chatbot"
}

resource "aws_api_gateway_method" "chatbot_post" {
  rest_api_id   = aws_api_gateway_rest_api.api.id
  resource_id   = aws_api_gateway_resource.chatbot.id
  http_method   = "POST"
  authorization = "NONE"
}

resource "aws_api_gateway_method" "chatbot_options" {
  rest_api_id   = aws_api_gateway_rest_api.api.id
  resource_id   = aws_api_gateway_resource.chatbot.id
  http_method   = "OPTIONS"
  authorization = "NONE"
}

resource "aws_api_gateway_integration" "chatbot_lambda" {
  rest_api_id             = aws_api_gateway_rest_api.api.id
  resource_id             = aws_api_gateway_resource.chatbot.id
  http_method             = aws_api_gateway_method.chatbot_post.http_method
  integration_http_method = "POST"
  type                    = "AWS_PROXY"
  uri                     = aws_lambda_function.chatbot.invoke_arn
}

resource "aws_api_gateway_integration" "chatbot_options_integration" {
  rest_api_id             = aws_api_gateway_rest_api.api.id
  resource_id             = aws_api_gateway_resource.chatbot.id
  http_method             = aws_api_gateway_method.chatbot_options.http_method
  integration_http_method = "POST"
  type                    = "AWS_PROXY"
  uri                     = aws_lambda_function.chatbot.invoke_arn
}

resource "aws_lambda_permission" "allow_apigw_chatbot" {
  statement_id  = "AllowAPIGatewayInvokeChatbot"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.chatbot.function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${aws_api_gateway_rest_api.api.execution_arn}/*/*"
}

# POST /remote-alert — Remote alert request from web
resource "aws_api_gateway_resource" "remote_alert" {
  rest_api_id = aws_api_gateway_rest_api.api.id
  parent_id   = aws_api_gateway_rest_api.api.root_resource_id
  path_part   = "remote-alert"
}

resource "aws_api_gateway_method" "remote_alert_post" {
  rest_api_id   = aws_api_gateway_rest_api.api.id
  resource_id   = aws_api_gateway_resource.remote_alert.id
  http_method   = "POST"
  authorization = "NONE"
}

resource "aws_api_gateway_integration" "remote_alert_lambda" {
  rest_api_id             = aws_api_gateway_rest_api.api.id
  resource_id             = aws_api_gateway_resource.remote_alert.id
  http_method             = aws_api_gateway_method.remote_alert_post.http_method
  integration_http_method = "POST"
  type                    = "AWS_PROXY"
  uri                     = aws_lambda_function.remote.invoke_arn
}

resource "aws_lambda_permission" "allow_apigw_remote" {
  statement_id  = "AllowAPIGatewayInvokeRemote"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.remote.function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${aws_api_gateway_rest_api.api.execution_arn}/*/*"
}

# API Gateway deployment (prod stage)
resource "aws_api_gateway_deployment" "prod" {
  rest_api_id = aws_api_gateway_rest_api.api.id

  triggers = {
    redeployment = sha1(jsonencode([
      aws_api_gateway_resource.inbound,
      aws_api_gateway_method.inbound_post,
      aws_api_gateway_integration.inbound_lambda,
      aws_api_gateway_resource.remote_alert,
      aws_api_gateway_method.remote_alert_post,
      aws_api_gateway_integration.remote_alert_lambda,
      aws_api_gateway_resource.chatbot,
      aws_api_gateway_method.chatbot_post,
      aws_api_gateway_integration.chatbot_lambda,
    ]))
  }

  lifecycle {
    create_before_destroy = true
  }

  depends_on = [
    aws_api_gateway_integration.inbound_lambda,
    aws_api_gateway_integration.remote_alert_lambda,
    aws_api_gateway_integration.chatbot_lambda,
  ]
}

resource "aws_cloudwatch_log_group" "api_gw_logs" {
  name              = "/aws/apigateway/smartscan-prod"
  retention_in_days = 30
}

resource "aws_api_gateway_stage" "prod" {
  deployment_id = aws_api_gateway_deployment.prod.id
  rest_api_id   = aws_api_gateway_rest_api.api.id
  stage_name    = "prod"
}

resource "aws_api_gateway_usage_plan" "default" {
  name = "smartscan-default"

  api_stages {
    api_id = aws_api_gateway_rest_api.api.id
    stage  = aws_api_gateway_stage.prod.stage_name
  }

  throttle_settings {
    rate_limit  = 10
    burst_limit = 20
  }
}

# ==========================================
# 9. S3 + CloudFront
# ==========================================
# S3 bucket for hosting React frontend static files
resource "aws_s3_bucket" "web" {
  bucket = "smartscan-hub-frontend"
}

# Block all public access to S3 bucket (CloudFront will access via OAC)
resource "aws_s3_bucket_public_access_block" "web_public_access" {
  bucket                  = aws_s3_bucket.web.id
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

# Origin Access Control for secure S3 access from CloudFront
resource "aws_cloudfront_origin_access_control" "oac" {
  name                              = "smartscan-s3-oac"
  description                       = "SmartScan S3 OAC"
  origin_access_control_origin_type = "s3"
  signing_behavior                  = "always"
  signing_protocol                  = "sigv4"
}

# CloudFront distribution for global CDN with custom domain support
resource "aws_cloudfront_distribution" "frontend" {
  origin {
    domain_name              = aws_s3_bucket.web.bucket_regional_domain_name
    origin_id                = "S3-smartscan-frontend"
    origin_access_control_id = aws_cloudfront_origin_access_control.oac.id
  }

  enabled             = true
  default_root_object = "index.html"
  aliases             = var.acm_cert_arn != "" ? ["smartscan-hub.com"] : []

  default_cache_behavior {
    allowed_methods        = ["GET", "HEAD", "OPTIONS"]
    cached_methods         = ["GET", "HEAD"]
    target_origin_id       = "S3-smartscan-frontend"
    viewer_protocol_policy = "redirect-to-https"
    compress               = true

    forwarded_values {
      query_string = false
      cookies { forward = "none" }
    }
  }

  restrictions {
    geo_restriction { restriction_type = "none" }
  }

  viewer_certificate {
    acm_certificate_arn      = var.acm_cert_arn
    ssl_support_method       = "sni-only"
    minimum_protocol_version = "TLSv1.2_2021"
  }

  tags = { Name = "smartscan-cloudfront" }
}

# S3 bucket policy allowing CloudFront OAC to read objects
resource "aws_s3_bucket_policy" "web_policy" {
  bucket     = aws_s3_bucket.web.id
  depends_on = [aws_s3_bucket_public_access_block.web_public_access]
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid    = "AllowCloudFrontOAC"
        Effect = "Allow"
        Principal = {
          Service = "cloudfront.amazonaws.com"
        }
        Action   = "s3:GetObject"
        Resource = "${aws_s3_bucket.web.arn}/*"
        Condition = {
          StringEquals = {
            "AWS:SourceArn" = aws_cloudfront_distribution.frontend.arn
          }
        }
      }
    ]
  })
}

# ==========================================
# 10. Outputs
# ==========================================
output "api_gateway_url" {
  description = "API Gateway base URL"
  value       = "https://${aws_api_gateway_rest_api.api.id}.execute-api.ap-northeast-2.amazonaws.com/prod"
}

output "cloudfront_domain" {
  description = "CloudFront domain"
  value       = aws_cloudfront_distribution.frontend.domain_name
}

# ==========================================
# 11. GitHub Actions OIDC (CI/CD)
# ==========================================
# OIDC provider for GitHub Actions to authenticate with AWS
resource "aws_iam_openid_connect_provider" "github" {
  url             = "https://token.actions.githubusercontent.com"
  client_id_list  = ["sts.amazonaws.com"]
  thumbprint_list = ["6938fd4d98bab03faadb97b34396831e3780aea1"]
}

# IAM role for GitHub Actions with repo-specific access
resource "aws_iam_role" "github_actions" {
  name = "github-actions-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect = "Allow"
      Principal = {
        Federated = aws_iam_openid_connect_provider.github.arn
      }
      Action = "sts:AssumeRoleWithWebIdentity"
      Condition = {
        StringEquals = {
          "token.actions.githubusercontent.com:aud" = "sts.amazonaws.com"
        }
        StringLike = {
          "token.actions.githubusercontent.com:sub" = "repo:${var.github_repo}:*"
        }
      }
    }]
  })
}

# [MODIFIED] Lambda deployment permissions: added remote + S3 + CloudFront
# Policy granting GitHub Actions permissions to deploy Lambda functions, S3 files, and invalidate CloudFront cache
resource "aws_iam_role_policy" "github_actions_lambda" {
  name = "github-actions-lambda-deploy"
  role = aws_iam_role.github_actions.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "lambda:UpdateFunctionCode",
          "lambda:GetFunction",
          "lambda:PublishVersion"
        ]
        Resource = [
          aws_lambda_function.inbound.arn,
          aws_lambda_function.outbound.arn,
          aws_lambda_function.remote.arn,
          aws_lambda_function.chatbot.arn
        ]
      },
      {
        Effect = "Allow"
        Action = [
          "s3:ListBucket",
          "s3:GetObject",
          "s3:PutObject",
          "s3:DeleteObject"
        ]
        Resource = [
          aws_s3_bucket.web.arn,
          "${aws_s3_bucket.web.arn}/*"
        ]
      },
      {
        Effect   = "Allow"
        Action   = ["cloudfront:CreateInvalidation"]
        Resource = aws_cloudfront_distribution.frontend.arn
      }
    ]
  })
}

output "github_actions_role_arn" {
  description = "GitHub Actions IAM Role ARN"
  value       = aws_iam_role.github_actions.arn
}
