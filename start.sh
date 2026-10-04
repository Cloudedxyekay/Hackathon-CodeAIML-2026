#!/usr/bin/env bash
exec python -m uvicorn server.main:app --app-dir project360-app --host 0.0.0.0 --port "${PORT:-8000}"
