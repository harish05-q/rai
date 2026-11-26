FROM node:22-bookworm-slim AS web
WORKDIR /build
COPY apps/web/package*.json ./
RUN npm ci
COPY apps/web/ ./
ENV NEXT_PUBLIC_API_BASE_URL="" \
    NEXT_PUBLIC_RAI_PUBLIC_DEMO=1 \
    RAI_DEMO_INTERNAL_API=http://127.0.0.1:8000 \
    NEXT_TELEMETRY_DISABLED=1
RUN npm run build

FROM python:3.12-slim-bookworm
RUN apt-get update && apt-get install -y --no-install-recommends libstdc++6 libatomic1 && rm -rf /var/lib/apt/lists/*
COPY --from=web /usr/local/bin/node /usr/local/bin/node
WORKDIR /app/api
COPY apps/api/requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt
COPY apps/api/app ./app
COPY --from=web /build/.next/standalone /app/web/
COPY --from=web /build/.next/static /app/web/.next/static
COPY --from=web /build/public /app/web/public
COPY deploy/run_demo.py ./
ENV NODE_ENV=production NEXT_TELEMETRY_DISABLED=1 PYTHONUNBUFFERED=1
USER 10001:10001
EXPOSE 10000
CMD ["python", "run_demo.py"]
