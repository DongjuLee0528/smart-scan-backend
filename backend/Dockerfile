FROM python:3.12-slim

WORKDIR /app

# 시스템 패키지 설치 (PyMySQL cryptography 빌드용)
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# 의존성 먼저 설치 (캐시 활용)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 소스 복사
COPY . .

# 포트 설정
EXPOSE 8000

# 실행
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000"]
