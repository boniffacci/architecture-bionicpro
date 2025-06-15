#!/bin/sh

PATH="/app/.venv/bin:$PATH"
export PATH

if [ x"$APP_MODE" = xDEV ];then
    exec fastapi dev --host "0.0.0.0" --port ${APP_PORT} --reload "$@"
else
    exec fastapi run --host "0.0.0.0" --port ${APP_PORT} --workers ${FASTAPI_WORKERS:-1} "$@"
fi

