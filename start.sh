\
#!/usr/bin/env bash
set -euo pipefail
export PYTHONUNBUFFERED=1

mkdir -p /data/uploads

DB_DEFAULT_NAME="${DB_FILENAME:-shop_bot.db}"
DB_PROJECT_PATH="/opt/render/project/src/${DB_DEFAULT_NAME}"
DB_DISK_PATH="/data/${DB_DEFAULT_NAME}"

if [[ -f "${DB_PROJECT_PATH}" && ! -f "${DB_DISK_PATH}" ]]; then
  cp "${DB_PROJECT_PATH}" "${DB_DISK_PATH}"
fi

ln -sf "${DB_DISK_PATH}" "${DB_PROJECT_PATH}" || true

rm -rf /opt/render/project/src/web_admin/uploads || true
ln -s /data/uploads /opt/render/project/src/web_admin/uploads || true

export DB_PATH="${DB_DISK_PATH}"
export UPLOAD_DIR="/data/uploads"
export ENVIRONMENT="${ENVIRONMENT:-production}"

python /opt/render/project/src/main.py &

cd /opt/render/project/src/web_admin
exec gunicorn -w 2 -k gthread -t 120 -b 0.0.0.0:$PORT app:app
