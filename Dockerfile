FROM python:3.10-slim-bookworm

WORKDIR /app

# libgomp1 is required by scikit-learn (OpenMP runtime).
# Some networks can't reach Debian's HTTP Fastly edges; HTTPS routes via
# different edges and is reliable. Switch sources to HTTPS, then retry apt
# to absorb any remaining transient mirror flakes.
RUN set -eux; \
    sed -i 's|http://deb.debian.org|https://deb.debian.org|g; s|http://security.debian.org|https://security.debian.org|g' \
        /etc/apt/sources.list.d/debian.sources 2>/dev/null || \
    sed -i 's|http://deb.debian.org|https://deb.debian.org|g; s|http://security.debian.org|https://security.debian.org|g' \
        /etc/apt/sources.list 2>/dev/null || true; \
    for i in 1 2 3; do \
        apt-get update && \
        apt-get install -y --no-install-recommends libgomp1 && \
        break || { echo "apt attempt $i failed, retrying..."; sleep 5; }; \
    done; \
    rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

COPY . .

# Render sets PORT; default 8000 for local Docker
CMD ["sh", "-c", "exec uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
