# SmartScan Hub

A touchless belongings check system using UHF RFID. Automatically scans items at the doorway as you leave and sends an email alert for anything you forgot.

---

## Architecture

```
Raspberry Pi (RFID Reader)
    │ HTTPS POST /inbound
    ▼
API Gateway
    ├─ /inbound      → Lambda: smartscan-inbound   (scan processing)
    ├─ /remote-alert → Lambda: smartscan-remote    (manual alert from web)
    └─ /chatbot      → Lambda: smartscan-chatbot   (Kakao chatbot)
                              ↓ invoke
                         Lambda: smartscan-outbound (email notification)
                              ↓ Resend API
                           Email

Web Frontend (S3 + CloudFront)  →  FastAPI (Render)  →  Supabase PostgreSQL
                                            ↑
                                     Supabase Auth
```

### Infrastructure
| Component | Service |
|---|---|
| Database | Supabase PostgreSQL |
| Authentication | Supabase Auth + Resend SMTP |
| Backend API | FastAPI on Render |
| Lambda (×4) | AWS Lambda (Python 3.11) |
| API Gateway | AWS API Gateway (prod stage) |
| Frontend | S3 + CloudFront |
| Domain | smartscan-hub.com (ACM TLS) |
| IaC | Terraform |
| CI/CD | GitHub Actions |

---

## Repository Structure

```
smart-scan-backend/
├── backend/                   # FastAPI backend (Render)
│   ├── app.py
│   ├── routes/
│   ├── services/
│   ├── repositories/
│   ├── models/
│   ├── schemas/
│   ├── common/
│   └── requirements.txt
│
├── lambdas/
│   ├── inbound-scanner/       # RFID scan handler
│   ├── outbound-notifier/     # Email notification sender
│   ├── remote-alert/          # Web-triggered manual alert
│   └── chatbot-skill-server/  # Kakao chatbot handler
│
├── terraform/                 # AWS infrastructure (IaC)
│   ├── main.tf
│   ├── terraform.tfvars       # gitignored — copy from .example
│   └── terraform.tfvars.example
│
└── .github/workflows/         # CI/CD pipelines
    ├── ci-backend.yml         # Syntax + import check on push/PR
    ├── deploy-inbound.yml
    ├── deploy-outbound.yml
    ├── deploy-remote.yml
    ├── deploy-chatbot.yml
    └── deploy-frontend.yml
```

---

## Database Schema (Supabase PostgreSQL)

| Table | Description |
|---|---|
| `profiles` | User profiles linked to Supabase Auth |
| `families` | Family group with owner |
| `family_members` | Members belonging to a family |
| `devices` | UHF RFID reader devices (identified by serial number) |
| `items` | Belongings registered per family member |
| `tags` | RFID tag registry (tag_uid → item mapping) |
| `scan_logs` | RFID scan event records (FOUND / LOST) |
| `notifications` | Email notification history |

---

## Lambda Functions

### inbound-scanner
Triggered by API Gateway POST `/inbound`. Receives RFID scan data from the Raspberry Pi, queries missing items, and directly invokes `outbound-notifier`.

### outbound-notifier
Invoked directly by `inbound-scanner`. Sends missing item alert emails via Resend API and records notifications in the database.

### remote-alert
Triggered by API Gateway POST `/remote-alert`. Allows web users to manually send an alert to a family member. Requires Supabase Bearer JWT in the `Authorization` header.

### chatbot-skill-server
Triggered by API Gateway POST `/chatbot`. Handles Kakao chatbot utterances for device registration, item management, and device unlinking.

---

## Backend API (FastAPI on Render)

Base URL: configured via Render environment variables.

| Router | Prefix | Description |
|---|---|---|
| auth | `/api/auth` | Sign up, login, token refresh |
| devices | `/api/devices` | Device registration and lookup |
| family_members | `/api/families/members` | Family member management |
| items | `/api/items` | Belongings CRUD |
| labels | `/api/labels` | RFID label management |
| tags | `/api/tags` | Tag-item mapping |
| scan_logs | `/api/scan-logs` | Scan history |
| notifications | `/api/notifications` | Notification history |
| monitoring | `/api/monitoring` | Device monitoring |

---

## CI/CD

### Automatic Deployment
| Trigger | Action |
|---|---|
| Push to `main` (backend/**) | CI syntax + import check |
| Push to `main` (lambdas/inbound-scanner/**) | Deploy `smartscan-inbound` Lambda |
| Push to `main` (lambdas/outbound-notifier/**) | Deploy `smartscan-outbound` Lambda |
| Push to `main` (lambdas/remote-alert/**) | Deploy `smartscan-remote` Lambda |
| Push to `main` (lambdas/chatbot-skill-server/**) | Deploy `smartscan-chatbot` Lambda |
| Push to `main` (frontend/**) | Sync to S3 + CloudFront invalidation |
| CI checks pass on `main` | Render auto-deploys FastAPI |

### Branch Strategy
- `qa` — development and integration testing
- `main` — production (protected, merge via PR)

### Required GitHub Secrets
| Secret | Description |
|---|---|
| `AWS_ROLE_ARN` | GitHub Actions OIDC role ARN |
| `CLOUDFRONT_DISTRIBUTION_ID` | CloudFront distribution ID |

---

## Infrastructure (Terraform)

Manages: API Gateway, Lambda functions, S3, CloudFront, IAM roles, OIDC provider.

```bash
cd terraform
cp terraform.tfvars.example terraform.tfvars
# Fill in terraform.tfvars

terraform init
terraform plan
terraform apply
```

### Required Variables
| Variable | Description |
|---|---|
| `supabase_url` | Supabase project URL |
| `supabase_service_key` | Supabase service role key |
| `resend_api_key` | Resend email API key |
| `acm_cert_arn` | ACM certificate ARN (us-east-1) |
| `github_repo` | GitHub repo in `owner/repo` format |
| `domain_name` | Custom domain (smartscan-hub.com) |

---

## Local Development

### FastAPI Backend

```bash
# Create virtual environment in project root
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate

# Install backend dependencies
cd backend
pip install -r requirements.txt

# Copy and fill in environment variables (replace MySQL vars with Supabase)
cp ../.env.example ../.env

# Run FastAPI server
uvicorn app:app --reload
# Swagger UI available at http://localhost:8000/docs (requires ENV=development)
```

### Lambda (local test)

```bash
cd lambdas/inbound-scanner
pip install -r requirements.txt

export SUPABASE_URL=your-url
export SUPABASE_SERVICE_KEY=your-key

python -c "from lambda_function import lambda_handler; print(lambda_handler({}, {}))"
```

---

## Environment Variables

### FastAPI (Render)
| Variable | Description |
|---|---|
| `DATABASE_URL` | Supabase PostgreSQL connection string |
| `JWT_SECRET_KEY` | Supabase JWT secret |
| `ALLOWED_ORIGIN` | Frontend origin for CORS |
| `ENV` | `development` enables `/docs` |

Note: For local development, copy `.env.example` to `.env` and update with your actual Supabase credentials instead of the MySQL placeholders.

### Lambda (AWS Console / Terraform)
| Variable | Description |
|---|---|
| `SUPABASE_URL` | Supabase project URL |
| `SUPABASE_SERVICE_KEY` | Supabase service role key |
| `RESEND_API_KEY` | Resend API key (outbound / remote only) |

---

## Hardware

- **Raspberry Pi 4B** — RFID controller
- **FI-805F UHF RFID Reader** (RS232) — 902–928 MHz, up to 5 m range
- **USB-to-RS232 Converter** — connects reader to Pi via `/dev/ttyUSB0`
- **Passive UHF Anti-Metal RFID Tags** — ISO 18000-6C, attached to belongings
