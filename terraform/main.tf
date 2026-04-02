terraform {
  required_version = ">= 1.5.0"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

variable "aws_region" {
  description = "AWS region used for the GitHub Actions deployment role and Lambda functions."
  type        = string
  default     = "ap-northeast-2"
}

variable "github_repository" {
  description = "GitHub repository allowed to assume the deployment role."
  type        = string
  default     = "DongjuLee0528/smart-scan-backend"
}

variable "github_actions_role_name" {
  description = "IAM role name assumed by GitHub Actions through OIDC."
  type        = string
  default     = "github-actions-role"
}

variable "lambda_function_names" {
  description = "Lambda function names that GitHub Actions can deploy."
  type        = list(string)
  default = [
    "inbound-scanner",
    "outbound-notifier",
    "chatbot-skill-server",
  ]
}

provider "aws" {
  region = var.aws_region
}

data "aws_caller_identity" "current" {}

locals {
  github_oidc_audience = "sts.amazonaws.com"
  github_oidc_subject  = "repo:${var.github_repository}:*"
  lambda_function_arns = [
    for function_name in var.lambda_function_names :
    "arn:aws:lambda:${var.aws_region}:${data.aws_caller_identity.current.account_id}:function:${function_name}"
  ]
}

resource "aws_iam_openid_connect_provider" "github" {
  url = "https://token.actions.githubusercontent.com"

  client_id_list = [
    local.github_oidc_audience,
  ]

  thumbprint_list = [
    "6938fd4d98bab03faadb97b34396831e3780aea1",
  ]
}

data "aws_iam_policy_document" "github_actions_assume_role" {
  statement {
    sid     = "GitHubActionsAssumeRole"
    actions = ["sts:AssumeRoleWithWebIdentity"]

    principals {
      type        = "Federated"
      identifiers = [aws_iam_openid_connect_provider.github.arn]
    }

    condition {
      test     = "StringEquals"
      variable = "token.actions.githubusercontent.com:aud"
      values   = [local.github_oidc_audience]
    }

    condition {
      test     = "StringLike"
      variable = "token.actions.githubusercontent.com:sub"
      values   = [local.github_oidc_subject]
    }
  }
}

resource "aws_iam_role" "github_actions_role" {
  name               = var.github_actions_role_name
  assume_role_policy = data.aws_iam_policy_document.github_actions_assume_role.json
}

data "aws_iam_policy_document" "github_actions_lambda_deploy" {
  statement {
    sid = "DeployLambdaCode"
    actions = [
      "lambda:GetFunction",
      "lambda:GetFunctionConfiguration",
      "lambda:UpdateFunctionCode",
    ]
    resources = local.lambda_function_arns
  }
}

resource "aws_iam_role_policy" "github_actions_lambda_deploy" {
  name   = "${var.github_actions_role_name}-lambda-deploy"
  role   = aws_iam_role.github_actions_role.id
  policy = data.aws_iam_policy_document.github_actions_lambda_deploy.json
}

output "github_actions_role_arn" {
  description = "IAM role ARN to store in the GITHUB_ACTIONS_ROLE_ARN repository secret."
  value       = aws_iam_role.github_actions_role.arn
}

output "github_oidc_provider_arn" {
  description = "GitHub Actions OIDC provider ARN."
  value       = aws_iam_openid_connect_provider.github.arn
}

output "github_actions_role_subject" {
  description = "Allowed GitHub Actions subject pattern for the trust policy."
  value       = local.github_oidc_subject
}
