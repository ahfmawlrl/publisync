#!/bin/bash
# Wait for MinIO to be ready, then create the default bucket
set -e

echo "Waiting for MinIO..."
until mc alias set local http://minio:9000 "${MINIO_ACCESS_KEY:-minioadmin}" "${MINIO_SECRET_KEY:-minioadmin}" 2>/dev/null; do
  sleep 2
done

echo "Creating bucket: publisync-media"
mc mb --ignore-existing local/publisync-media

echo "Setting bucket policy to private"
mc anonymous set none local/publisync-media

echo "MinIO initialization complete."
