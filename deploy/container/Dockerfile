# IGNIS demo container: serves the built frontend and proxies /api to the
# loopback-only workflow API (see deploy/README.md and docs/DEPLOYMENT.md).
# Caddy listens on $PORT (set by Render; 7860 when unset).

FROM node:24-slim AS web
WORKDIR /web
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci --no-audit --no-fund
COPY frontend/ ./
RUN VITE_API_BASE=/api npm run build

FROM caddy:2.8.4 AS caddy

FROM python:3.12-slim
ENV PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    IGNIS_MODE=replay \
    IGNIS_DATA=/tmp/ignis \
    XDG_DATA_HOME=/tmp/caddy-data \
    XDG_CONFIG_HOME=/tmp/caddy-config
WORKDIR /app

COPY requirements.txt ./
RUN pip install -r requirements.txt

# The official binary carries a cap_net_bind_service file capability, which hosts
# such as Render refuse to exec ("Operation not permitted"). `install` copies the
# binary without that xattr; Caddy only binds $PORT (>1024), so it is not needed.
COPY --from=caddy /usr/bin/caddy /tmp/caddy
RUN install -m 0755 /tmp/caddy /usr/local/bin/caddy && rm /tmp/caddy \
 && python -c "import os, sys; sys.exit('caddy still has file capabilities' if 'security.capability' in os.listxattr('/usr/local/bin/caddy') else 0)" \
 && caddy version
COPY . .
COPY --from=web /web/dist /app/frontend/dist

# MaintIE few-shot examples are needed only for IGNIS_MODE=live; pinned and hash-checked.
RUN python scripts/fetch_maintie.py

RUN useradd -m -u 1000 ignis && chown -R ignis /app
USER ignis

EXPOSE 10000
CMD ["sh", "deploy/container/start.sh"]
