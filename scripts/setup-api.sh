#!/bin/bash
# Устанавливает NOTA API как systemd-сервис
# Запускать один раз на сервере: bash /var/www/nota/scripts/setup-api.sh

set -e
cd /var/www/nota

echo "📦 Устанавливаем зависимости..."
venv/bin/pip install -q flask flask-cors gunicorn

echo "⚙️  Регистрируем systemd-сервис..."
cp nota-api.service /etc/systemd/system/nota-api.service
systemctl daemon-reload
systemctl enable nota-api
systemctl restart nota-api

echo "✅ API запущен:"
systemctl status nota-api --no-pager
