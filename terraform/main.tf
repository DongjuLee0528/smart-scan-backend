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
# variables.tf 내용 (민감 정보 분리)
# 실제 운영 시 terraform.tfvars 파일에 값 입력
# .gitignore에 terraform.tfvars 반드시 추가!
# ==========================================

# [수정] db_password, kakao_token 제거 → Supabase 변수로 교체
variable "supabase_url" {
  description = "Supabase 프로젝트 URL"
  type        = string
}

variable "supabase_service_key" {
  description = "Supabase Service Role Key (서버 전용)"
  type        = string
  sensitive   = true
}

variable "resend_api_key" {
  description = "Resend 이메일 API Key"
  type        = string
  sensitive   = true
}

variable "db_password" {
  description = "RDS 마스터 비밀번호"
  type        = string
  sensitive   = true
}

variable "acm_cert_arn" {
  description = "CloudFront용 ACM 인증서 ARN (us-east-1 리전 발급 필수)"
  type        = string
}

# [수정] github_repo 기본값: smart-scan-backend → smart-scan
variable "github_repo" {
  description = "GitHub 레포 경로 (owner/repo 형식)"
  type        = string
  default     = "DongjuLee0528/smart-scan"
}

# ==========================================
# 1. Provider 및 기본 VPC 설정
# ==========================================
provider "aws" {
  region = "ap-northeast-2"
}

resource "aws_vpc" "main" {
  cidr_block           = "10.0.0.0/16"
  enable_dns_hostnames = true
  enable_dns_support   = true
  tags                 = { Name = "smartscan-vpc" }
}

# ==========================================
# 2. 서브넷(Subnet) 및 게이트웨이(IGW)
# ==========================================
resource "aws_internet_gateway" "igw" {
  vpc_id = aws_vpc.main.id
  tags   = { Name = "smartscan-igw" }
}

resource "aws_subnet" "public_a" {
  vpc_id                  = aws_vpc.main.id
  cidr_block              = "10.0.1.0/24"
  availability_zone       = "ap-northeast-2a"
  map_public_ip_on_launch = true
  tags                    = { Name = "smartscan-public-subnet" }
}

resource "aws_subnet" "private_a" {
  vpc_id            = aws_vpc.main.id
  cidr_block        = "10.0.2.0/24"
  availability_zone = "ap-northeast-2a"
  tags              = { Name = "smartscan-private-subnet-a" }
}

resource "aws_subnet" "private_c" {
  vpc_id            = aws_vpc.main.id
  cidr_block        = "10.0.3.0/24"
  availability_zone = "ap-northeast-2c"
  tags              = { Name = "smartscan-private-subnet-c" }
}

# ==========================================
# 3. 라우팅 테이블 및 S3 엔드포인트
# ==========================================
resource "aws_route_table" "public_rt" {
  vpc_id = aws_vpc.main.id
  route {
    cidr_block = "0.0.0.0/0"
    gateway_id = aws_internet_gateway.igw.id
  }
}
resource "aws_route_table_association" "public_a_assoc" {
  subnet_id      = aws_subnet.public_a.id
  route_table_id = aws_route_table.public_rt.id
}

resource "aws_route_table" "private_rt" {
  vpc_id = aws_vpc.main.id
  tags   = { Name = "smartscan-private-rt" }
}
resource "aws_route_table_association" "private_a_assoc" {
  subnet_id      = aws_subnet.private_a.id
  route_table_id = aws_route_table.private_rt.id
}
resource "aws_route_table_association" "private_c_assoc" {
  subnet_id      = aws_subnet.private_c.id
  route_table_id = aws_route_table.private_rt.id
}

resource "aws_vpc_endpoint" "s3_gw" {
  vpc_id            = aws_vpc.main.id
  service_name      = "com.amazonaws.ap-northeast-2.s3"
  vpc_endpoint_type = "Gateway"
  route_table_ids   = [aws_route_table.private_rt.id]
}

# ==========================================
# 4. 보안 그룹 (Security Groups)
# ==========================================
# [수정] RDS 3306 rule 제거 (Supabase는 퍼블릭 HTTPS) → 443만 유지
resource "aws_security_group" "lambda_in_sg" {
  name   = "lambda-inbound-sg"
  vpc_id = aws_vpc.main.id

  egress {
    from_port   = 443
    to_port     = 443
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }
}

# [제거] rds_sg, lambda_to_rds, rds_from_lambda → RDS 미사용으로 제거

# ==========================================
# 5. IAM 역할 (Lambda Execution Role)
# ==========================================
data "aws_iam_policy_document" "lambda_assume_role" {
  statement {
    actions = ["sts:AssumeRole"]
    principals {
      type        = "Service"
      identifiers = ["lambda.amazonaws.com"]
    }
  }
}

resource "aws_iam_role" "lambda_role" {
  name               = "smartscan-lambda-role"
  assume_role_policy = data.aws_iam_policy_document.lambda_assume_role.json
}

resource "aws_iam_role_policy_attachment" "lambda_logs" {
  role       = aws_iam_role.lambda_role.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}

resource "aws_iam_role_policy_attachment" "lambda_vpc_access" {
  role       = aws_iam_role.lambda_role.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaVPCAccessExecutionRole"
}

# [수정] EventBridge 정책 제거 → Inbound→Outbound/Remote Lambda 직접 호출 정책으로 교체
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
# 6. RDS (주석 처리 - Supabase 마이그레이션 완료)
# 팀 확인 후 완전 제거 예정. prevent_destroy로 실수 방지.
# ==========================================
data "aws_db_subnet_group" "db_subnets" {
  name = "main-db-subnets"
}

resource "aws_db_instance" "smart_home" {
  allocated_storage      = 20
  engine                 = "mysql"
  engine_version         = "8.0"
  instance_class         = "db.t3.micro"
  db_name                = "smart_home"
  username               = "admin"
  password               = var.db_password
  multi_az               = true
  publicly_accessible    = true
  db_subnet_group_name   = data.aws_db_subnet_group.db_subnets.name
  vpc_security_group_ids = ["sg-0d7ea09356309516b"]
  skip_final_snapshot    = true

  lifecycle {
    prevent_destroy = true  # Supabase 안정화 전까지 실수 삭제 방지
    ignore_changes  = [password, engine_version]
  }
}

# ==========================================
# 7. Lambda 함수
# ==========================================
data "archive_file" "dummy_lambda" {
  type        = "zip"
  output_path = "${path.module}/dummy_payload.zip"
  source {
    content  = "def lambda_handler(event, context): return {'statusCode': 200, 'body': 'Init'}"
    filename = "lambda_function.py"
  }
}

# [수정] Inbound Lambda: VPC 제거 (Supabase 퍼블릭), 환경변수 Supabase로 변경
resource "aws_lambda_function" "inbound" {
  function_name    = "smartscan-inbound"
  role             = aws_iam_role.lambda_role.arn
  handler          = "lambda_function.lambda_handler"
  runtime          = "python3.12"
  timeout          = 30
  filename         = data.archive_file.dummy_lambda.output_path
  source_code_hash = data.archive_file.dummy_lambda.output_base64sha256
  reserved_concurrent_executions = 5

  # [수정] vpc_config 제거 (Supabase 퍼블릭 엔드포인트, NAT 불필요)

  environment {
    variables = {
      SUPABASE_URL         = var.supabase_url
      SUPABASE_SERVICE_KEY = var.supabase_service_key
    }
  }

  lifecycle {
    ignore_changes = [filename, source_code_hash]  # GitHub Actions가 코드 배포
  }
}

# [수정] Outbound Lambda: 환경변수 Supabase + Resend로 변경 (Kakao 제거)
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

# [추가] Remote Alert Lambda
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

# [제거] EventBridge 관련 리소스 모두 제거
# - aws_cloudwatch_event_rule.missing_item_rule
# - aws_cloudwatch_event_target.trigger_outbound_lambda
# - aws_lambda_permission.allow_eventbridge
# Inbound Lambda에서 Outbound Lambda 직접 호출 방식으로 변경

# ==========================================
# 8. API Gateway
# ==========================================
resource "aws_api_gateway_rest_api" "api" {
  name = "SmartScan-API"
}

# POST /inbound — 라즈베리파이 RFID 스캔 수신
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

# POST /remote-alert — 웹에서 원격 알림 요청
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

# API Gateway 배포 (prod 스테이지)
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
    ]))
  }

  lifecycle {
    create_before_destroy = true
  }

  depends_on = [
    aws_api_gateway_integration.inbound_lambda,
    aws_api_gateway_integration.remote_alert_lambda,
  ]
}

resource "aws_api_gateway_stage" "prod" {
  deployment_id = aws_api_gateway_deployment.prod.id
  rest_api_id   = aws_api_gateway_rest_api.api.id
  stage_name    = "prod"
}

# ==========================================
# 9. S3 + CloudFront
# ==========================================
resource "aws_s3_bucket" "web" {
  bucket = "smartscan-hub-frontend"
}

resource "aws_s3_bucket_public_access_block" "web_public_access" {
  bucket                  = aws_s3_bucket.web.id
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_cloudfront_origin_access_control" "oac" {
  name                              = "smartscan-s3-oac"
  description                       = "SmartScan S3 OAC"
  origin_access_control_origin_type = "s3"
  signing_behavior                  = "always"
  signing_protocol                  = "sigv4"
}

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
# 10. 출력값 (Outputs)
# ==========================================
output "rds_endpoint" {
  description = "RDS 엔드포인트 (Supabase 마이그레이션 완료 후 제거 예정)"
  value       = aws_db_instance.smart_home.endpoint
}

output "api_gateway_url" {
  description = "API Gateway 베이스 URL"
  value       = "https://${aws_api_gateway_rest_api.api.id}.execute-api.ap-northeast-2.amazonaws.com/prod"
}

output "cloudfront_domain" {
  description = "CloudFront 도메인"
  value       = aws_cloudfront_distribution.frontend.domain_name
}

# ==========================================
# 11. GitHub Actions OIDC (CI/CD)
# ==========================================
resource "aws_iam_openid_connect_provider" "github" {
  url             = "https://token.actions.githubusercontent.com"
  client_id_list  = ["sts.amazonaws.com"]
  thumbprint_list = ["6938fd4d98bab03faadb97b34396831e3780aea1"]
}

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

# [수정] Lambda 배포 권한: remote 추가 + S3 + CloudFront 추가
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
          "arn:aws:lambda:ap-northeast-2:771004632699:function:smartscan-chatbot"
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
