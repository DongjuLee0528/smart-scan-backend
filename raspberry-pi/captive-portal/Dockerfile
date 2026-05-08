FROM python:3.11-slim-bookworm

RUN apt-get update && apt-get install -y --no-install-recommends \
    hostapd \
    dnsmasq \
    wireless-tools \
    wpasupplicant \
    net-tools \
    iproute2 \
    isc-dhcp-client \
    iw \
    rfkill \
    procps \
    wget \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN mkdir -p /etc/smartscan /etc/wpa_supplicant /app/static && \
    wget -q -O /app/static/bootstrap.min.css \
    https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css

CMD ["python", "app.py"]
