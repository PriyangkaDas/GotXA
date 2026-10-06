FROM kalilinux/kali-rolling

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update && apt-get install -y \
    python3 \
    python3-pip \
    python3-requests \
    python3-urllib3 \
    python3-colorama \
    curl \
    wget \
    nmap \
    iputils-ping \
    net-tools \
    dnsutils \
    && rm -rf /var/lib/apt/lists/*

# Install pymodbus for OT/SCADA script support
RUN pip3 install --no-cache-dir --break-system-packages pymodbus>=3.5.0 || true

WORKDIR /workspace

COPY . .
RUN chmod +x run_all_attacks.sh menu.py 2>/dev/null || true

CMD ["tail", "-f", "/dev/null"]
