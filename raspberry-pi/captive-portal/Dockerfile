FROM python:3.11-slim-bookworm

RUN apt-get update && apt-get install -y --no-install-recommends \
    hostapd \
    dnsmasq \
    wireless-tools \
    wpasupplicant \
    net-tools \
    iproute2 \
    isc-dhcp-client \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN mkdir -p /etc/smartscan /etc/wpa_supplicant

CMD ["python", "app.py"]
