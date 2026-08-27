#!/usr/bin/env bash
set -e

echo "🤖 AutoAgent Setup"
echo "=================="

# Check for .env
if [ ! -f .env ]; then
  cp .env.example .env
  echo "✅ Created .env from .env.example"
  echo "⚠️  Please edit .env and add your API keys before running!"
  echo ""
  echo "Required keys:"
  echo "  GROQ_API_KEY     — from console.groq.com (free)"
  echo "  TAVILY_API_KEY   — from app.tavily.com (free tier available)"
  echo ""
  echo "Optional:"
  echo "  OPENAI_API_KEY   — for GPT-4o support"
  echo "  ANTHROPIC_API_KEY — for Claude support"
  echo ""
fi

# Start services
echo "🐳 Starting Docker services..."
docker compose up -d postgres redis

echo "⏳ Waiting for Postgres..."
sleep 3

echo "🗄️  Running migrations..."
docker compose run --rm backend alembic upgrade head || true

echo ""
echo "🚀 Starting AutoAgent..."
echo "  Backend:  http://localhost:8000"
echo "  Frontend: http://localhost:5173"
echo "  API docs: http://localhost:8000/docs"
echo ""

docker compose up
