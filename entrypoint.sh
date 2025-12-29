#!/bin/sh
# Читаем дату из файла и экспортируем в переменную
export APP_BUILD_TIME=$(cat /app/build_date.txt)
echo "Application build time: $APP_BUILD_TIME"
# Запускаем основную команду (Gunicorn)
exec "$@"