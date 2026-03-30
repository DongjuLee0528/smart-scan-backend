# ==========================================
# variables.tf 내용 (민감 정보 분리)
# 실제 운영 시 terraform.tfvars 파일에 값 입력
# .gitignore에 terraform.tfvars 반드시 추가!
# ==========================================
variable "db_password" {
  description = "RDS 마스터 패스워드"
  type        = string
  sensitive   = true # plan/apply 출력에서 마스킹
}

variable "kakao_token" {
  description = "카카오 REST API 액세스 토큰"
  type        = string
  sensitive   = true
}

variable "acm_cert_arn" {
  description = "CloudFront용 ACM 인증서 ARN (us-east-1 리전 발급 필수)"
  type        = string
  default     = "" # 인증서 발급 전 임시 빈 값
}

# ==========================================
# 1. Provider 및 기본 VPC 설정
# ==========================================
provider "aws" {
  region = "ap-northeast-2"
}

# [수정] VPC 이름: smart-home-vpc → smartscan-vpc (프로젝트 명칭 통일)
resource "aws_vpc" "main" {
  cidr_block           = "10.0.0.0/16"
  enable_dns_hostnames = true
  enable_dns_support   = true # [추가] DNS 지원 명시
  tags                 = { Name = "smartscan-vpc" }
}

# ==========================================
# 2. 서브넷(Subnet) 및 게이트웨이(IGW)
# ==========================================
# [수정] IGW 이름: main-igw → smartscan-igw
resource "aws_internet_gateway" "igw" {
  vpc_id = aws_vpc.main.id
  tags   = { Name = "smartscan-igw" }
}

# [수정] Public 서브넷 태그 통일
resource "aws_subnet" "public_a" {
  vpc_id                  = aws_vpc.main.id
  cidr_block              = "10.0.1.0/24"
  availability_zone       = "ap-northeast-2a"
  map_public_ip_on_launch = true
  tags                    = { Name = "smartscan-public-subnet" }
}

# [수정] Private 서브넷 CIDR 변경: 10.0.100.0/24 → 10.0.2.0/24 (노션 VPC 리소스맵 기준)
resource "aws_subnet" "private_a" {
  vpc_id            = aws_vpc.main.id
  cidr_block        = "10.0.2.0/24"
  availability_zone = "ap-northeast-2a"
  tags              = { Name = "smartscan-private-subnet-a" }
}

# [수정] Private 서브넷 CIDR 변경: 10.0.200.0/24 → 10.0.3.0/24 (노션 VPC 리소스맵 기준)
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
# [수정] Lambda SG egress: 전체 트래픽 허용 → 3306(RDS 전용) + 443(EventBridge) 최소 권한 원칙 적용
resource "aws_security_group" "lambda_in_sg" {
  name   = "lambda-inbound-sg"
  vpc_id = aws_vpc.main.id

  # EventBridge HTTPS 아웃바운드
  egress {
    from_port   = 443
    to_port     = 443
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }
}

resource "aws_security_group" "rds_sg" {
  name   = "rds-sg"
  vpc_id = aws_vpc.main.id
}

# 순환 참조 방지: SG Rule 분리 선언
resource "aws_security_group_rule" "lambda_to_rds" {
  type                     = "egress"
  from_port                = 3306
  to_port                  = 3306
  protocol                 = "tcp"
  security_group_id        = aws_security_group.lambda_in_sg.id
  source_security_group_id = aws_security_group.rds_sg.id
}

resource "aws_security_group_rule" "rds_from_lambda" {
  type                     = "ingress"
  from_port                = 3306
  to_port                  = 3306
  protocol                 = "tcp"
  security_group_id        = aws_security_group.rds_sg.id
  source_security_group_id = aws_security_group.lambda_in_sg.id
}

# ==========================================
# 5. IAM 역할 (Lambda Execution Role) & 런타임 권한
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

# [수정] IAM 역할 이름: iot_lambda_execution_role → smartscan-lambda-role (프로젝트 명칭 통일)
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

# [수정] EventBridge 권한 Resource: 특정 버스 ARN → "*" (default 버스 사용으로 변경됨에 따른 수정)
resource "aws_iam_role_policy" "lambda_eventbridge_policy" {
  name   = "lambda-eventbridge-putevents"
  role   = aws_iam_role.lambda_role.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect   = "Allow"
        Action   = ["events:PutEvents"]
        Resource = "*" # default 버스 사용으로 와일드카드 적용
      }
    ]
  })
}

# ==========================================
# 6. RDS (MySQL Multi-AZ)
# ==========================================
# 기존 AWS에서 생성된 subnet group 참조 (재생성하지 않음)
data "aws_db_subnet_group" "db_subnets" {
  name = "main-db-subnets"
}

# [수정] 복수 항목 수정
#   - resource 이름: mysql → smart_home (노션 DB 통합 기준)
#   - db_name: smart_home_db → smart_home (노션 "DB 스키마 단일화" 결정 사항)
#   - multi_az: false → true (비기능 요구사항: 고가용성 RDS Multi-AZ)
#   - publicly_accessible: true 추가 (개발/디버깅 단계 접속용, 운영 시 false 전환 권장)
#   - username/password: 변수 참조 권장 (현재는 개발 편의상 유지, 운영 시 var.db_password 사용)
resource "aws_db_instance" "smart_home" {
  allocated_storage      = 20
  engine                 = "mysql"
  engine_version         = "8.0"
  instance_class         = "db.t3.micro"
  db_name                = "smart_home"          # [수정] smart_home_db → smart_home
  username               = "admin"
  password               = var.db_password       # [수정] 하드코딩 제거 → 변수 참조
  multi_az               = true                  # [수정] false → true (Multi-AZ 고가용성)
  publicly_accessible    = true                  # [추가] 개발 단계 외부 접속 허용 (운영 시 false 권장)
  db_subnet_group_name   = data.aws_db_subnet_group.db_subnets.name
  vpc_security_group_ids = ["sg-0d7ea09356309516b"] # 기존 VPC의 rds-sg
  skip_final_snapshot    = true
}

# ==========================================
# 7. 서버리스 로직: Lambda & EventBridge
# ==========================================
data "archive_file" "dummy_lambda" {
  type        = "zip"
  output_path = "${path.module}/dummy_payload.zip"
  source {
    content  = "def lambda_handler(event, context): return {'statusCode': 200, 'body': 'Init'}"
    filename = "lambda_function.py" # [수정] index.py → lambda_function.py (핸들러 명칭과 일치)
  }
}

# [수정] Inbound Lambda
#   - function_name: Inbound-Scanner → smartscan-inbound
#   - runtime: python3.9 → python3.12 (노션 Tech Stack 기준)
#   - handler: index.handler → lambda_function.lambda_handler
#   - timeout 추가: 30초
#   - environment 변수 추가: DB 연결 정보 (환경 변수로 민감 정보 관리)
resource "aws_lambda_function" "inbound" {
  function_name    = "smartscan-inbound"
  role             = aws_iam_role.lambda_role.arn
  handler          = "lambda_function.lambda_handler" # [수정] index.handler → lambda_function.lambda_handler
  runtime          = "python3.12"                     # [수정] python3.9 → python3.12
  timeout          = 30                               # [추가] 타임아웃 명시
  filename         = data.archive_file.dummy_lambda.output_path
  source_code_hash = data.archive_file.dummy_lambda.output_base64sha256
  reserved_concurrent_executions = 5

  vpc_config {
    subnet_ids         = [aws_subnet.private_a.id, aws_subnet.private_c.id]
    security_group_ids = [aws_security_group.lambda_in_sg.id]
  }

  # [추가] 환경 변수: DB 접속 정보 (하드코딩 금지 원칙 준수)
  environment {
    variables = {
      DB_HOST     = aws_db_instance.smart_home.address
      DB_USER     = "admin"
      DB_PASSWORD = var.db_password
      DB_NAME     = "smart_home"
    }
  }
}

# [수정] Custom EventBus(ItemScanBus) 제거 → default 버스 사용
# EventBridge default 버스는 별도 리소스 선언 불필요
# (Inbound Lambda 코드에서 EventBusName = "default" 로 발행)

# [수정] EventBridge 규칙
#   - name: capture-missing-items → smartscan-missing-item-rule
#   - source: smart.home.scanner → smartscan.inbound (노션 이벤트 스키마 기준)
#   - detail-type: ItemMissingEvent → MissingItemDetected (노션 이벤트 스키마 기준)
#   - event_bus_name 제거 (default 버스 사용)
resource "aws_cloudwatch_event_rule" "missing_item_rule" {
  name        = "smartscan-missing-item-rule"
  description = "소지품 누락 감지 시 Outbound Lambda 트리거"
  event_pattern = jsonencode({
    "source"      = ["smartscan.inbound"]       # [수정] smart.home.scanner → smartscan.inbound
    "detail-type" = ["MissingItemDetected"]     # [수정] ItemMissingEvent → MissingItemDetected
  })
  # event_bus_name 제거 → default 버스 사용
}

# [수정] Outbound Lambda
#   - function_name: Outbound-Notifier → smartscan-outbound
#   - runtime: python3.9 → python3.12
#   - handler: index.handler → lambda_function.lambda_handler
#   - timeout 추가: 15초
#   - vpc_config 없음 유지 (VPC 외부에서 카카오 API 직접 호출)
#   - environment 변수 추가: 카카오 토큰
resource "aws_lambda_function" "outbound" {
  function_name    = "smartscan-outbound"
  role             = aws_iam_role.lambda_role.arn
  handler          = "lambda_function.lambda_handler" # [수정] index.handler → lambda_function.lambda_handler
  runtime          = "python3.12"                     # [수정] python3.9 → python3.12
  timeout          = 15                               # [추가] 타임아웃 명시
  filename         = data.archive_file.dummy_lambda.output_path
  source_code_hash = data.archive_file.dummy_lambda.output_base64sha256
  reserved_concurrent_executions = 5
  # vpc_config 없음 → 인터넷 직접 접근으로 카카오 API 호출 가능 (NAT Gateway 불필요)

  # [추가] 환경 변수: 카카오 토큰 (하드코딩 금지 원칙 준수)
  environment {
    variables = {
      KAKAO_ACCESS_TOKEN = var.kakao_token
    }
  }
}

# [수정] EventBridge Target
#   - event_bus_name 제거 (default 버스 사용)
#   - target_id: SendTelegramNotification → OutboundLambdaTarget (카카오로 변경됨에 따른 수정)
resource "aws_cloudwatch_event_target" "trigger_outbound_lambda" {
  rule      = aws_cloudwatch_event_rule.missing_item_rule.name
  target_id = "OutboundLambdaTarget"             # [수정] SendTelegramNotification → OutboundLambdaTarget
  arn       = aws_lambda_function.outbound.arn
  # event_bus_name 제거 → default 버스 사용
}

resource "aws_lambda_permission" "allow_eventbridge" {
  statement_id  = "AllowEventBridgeInvoke"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.outbound.function_name
  principal     = "events.amazonaws.com"
  source_arn    = aws_cloudwatch_event_rule.missing_item_rule.arn
}

# ==========================================
# 8. API Gateway & Cognito
# ==========================================
resource "aws_api_gateway_rest_api" "api" {
  name = "SmartScan-API" # [수정] RFID-Scan-API → SmartScan-API
}

resource "aws_cognito_user_pool" "pool" {
  name = "UserAuthPool"
}

# ==========================================
# 9. S3 + CloudFront (정식 도메인 HTTPS 호스팅)
# ==========================================
# [수정] S3 버킷: 퍼블릭 웹호스팅 방식 → CloudFront OAC 방식으로 전환
#   - 버킷명: smart-home-scanner-web-hosting-team5 → smartscan-hub-frontend
#   - 퍼블릭 접근 전면 차단 (CloudFront를 통해서만 접근)
resource "aws_s3_bucket" "web" {
  bucket = "smartscan-hub-frontend" # [수정] 명칭 통일 및 CloudFront 방식 전환
}

# [수정] 퍼블릭 액세스 전면 차단 (CloudFront OAC 방식 사용)
resource "aws_s3_bucket_public_access_block" "web_public_access" {
  bucket                  = aws_s3_bucket.web.id
  block_public_acls       = true  # [수정] false → true
  block_public_policy     = true  # [수정] false → true
  ignore_public_acls      = true  # [수정] false → true
  restrict_public_buckets = true  # [수정] false → true
}

# [추가] CloudFront Origin Access Control (OAC) - S3 직접 노출 방지
resource "aws_cloudfront_origin_access_control" "oac" {
  name                              = "smartscan-s3-oac"
  description                       = "SmartScan S3 OAC"
  origin_access_control_origin_type = "s3"
  signing_behavior                  = "always"
  signing_protocol                  = "sigv4"
}

# [추가] CloudFront 배포 - 정식 도메인 smartscan-hub.com + HTTPS 강제
resource "aws_cloudfront_distribution" "frontend" {
  origin {
    domain_name              = aws_s3_bucket.web.bucket_regional_domain_name
    origin_id                = "S3-smartscan-frontend"
    origin_access_control_id = aws_cloudfront_origin_access_control.oac.id
  }

  enabled             = true
  default_root_object = "index.html"
  aliases             = var.acm_cert_arn != "" ? ["smartscan-hub.com"] : [] # ACM 인증서 있을 때만 도메인 연결

  default_cache_behavior {
    allowed_methods        = ["GET", "HEAD", "OPTIONS"]
    cached_methods         = ["GET", "HEAD"]
    target_origin_id       = "S3-smartscan-frontend"
    viewer_protocol_policy = "redirect-to-https" # HTTP → HTTPS 강제
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
    cloudfront_default_certificate = true
  }

  tags = { Name = "smartscan-cloudfront" }
}

# [추가] S3 버킷 정책: CloudFront OAC에서만 접근 허용
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

# [제거] aws_s3_bucket_website_configuration - CloudFront OAC 방식에서는 불필요

# ==========================================
# 10. 팀원 전달용 결과 출력 (Outputs)
# ==========================================
output "rds_endpoint" {
  description = "백엔드 팀원이 연결할 DB 주소"
  value       = aws_db_instance.smart_home.endpoint # [수정] mysql → smart_home (리소스명 변경 반영)
}

# [수정] api_gateway_id → api_gateway_url (노션 협업 인터페이스 기준: api_gateway_url 출력)
output "api_gateway_url" {
  description = "프론트/엣지/챗봇 팀원이 호출할 API Gateway 베이스 URL"
  value       = "https://${aws_api_gateway_rest_api.api.id}.execute-api.ap-northeast-2.amazonaws.com/prod"
}

# [추가] CloudFront 도메인 출력 (노션 협업 인터페이스 기준: cloudfront_domain 출력)
output "cloudfront_domain" {
  description = "프론트엔드 팀원이 배포할 CloudFront 도메인 주소"
  value       = aws_cloudfront_distribution.frontend.domain_name
}

# ==========================================
# 11. GitHub Actions OIDC (CI/CD 자동 배포)
# ==========================================
variable "github_repo" {
  description = "GitHub 레포 경로 (owner/repo 형식)"
  type        = string
  default     = "DongjuLee0528/smart-scan-backend"
}

# GitHub OIDC Provider
resource "aws_iam_openid_connect_provider" "github" {
  url             = "https://token.actions.githubusercontent.com"
  client_id_list  = ["sts.amazonaws.com"]
  thumbprint_list = ["6938fd4d98bab03faadb97b34396831e3780aea1"]
}

# GitHub Actions IAM Role
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

# Lambda 배포 권한
resource "aws_iam_role_policy" "github_actions_lambda" {
  name = "github-actions-lambda-deploy"
  role = aws_iam_role.github_actions.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect = "Allow"
      Action = [
        "lambda:UpdateFunctionCode",
        "lambda:GetFunction",
        "lambda:PublishVersion"
      ]
      Resource = [
        aws_lambda_function.inbound.arn,
        aws_lambda_function.outbound.arn,
        "arn:aws:lambda:ap-northeast-2:*:function:Chatbot-Skill-Server"
      ]
    }]
  })
}

output "github_actions_role_arn" {
  description = "GitHub Actions에서 사용할 IAM Role ARN (GitHub Secrets에 등록)"
  value       = aws_iam_role.github_actions.arn
}
