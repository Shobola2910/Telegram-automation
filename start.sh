#!/bin/bash
# ============================================
# ELD Monitor — Start Script
# ============================================

# Copy .env if not exists
if [ ! -f .env ]; then
  cp .env.example .env
  echo "⚠️  .env fayl yaratildi — uni to'ldiring!"
fi

# Install dependencies
pip install -r requirements.txt

# Start the server
uvicorn main:app --host 0.0.0.0 --port ${PORT:-8000} --reload
