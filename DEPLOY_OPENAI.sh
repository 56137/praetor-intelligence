#!/bin/bash
set -euo pipefail

pip install -r requirements.txt openai
gunicorn --bind :8080 --workers 1 --threads 8 --timeout 0 openai_wsgi_v2:app
