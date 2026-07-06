#!/bin/bash

echo "==================================="
echo " Voice AI System - Startup Script"
echo "==================================="

# Check if .env exists
if [ ! -f .env ]; then
    echo "Creating .env from .env.example..."
    cp .env.example .env
    echo "Please edit .env file with your settings"
fi

# Start services
echo "Starting Docker services..."
docker-compose up -d

echo ""
echo "==================================="
echo " Services Started!"
echo "==================================="
echo ""
echo " Frontend:     http://localhost:3000"
echo " Backend API:  http://localhost:8000/docs"
echo " AI Engine:    http://localhost:8001/docs"
echo " MinIO:        http://localhost:9001"
echo ""
echo " Default Login: admin / admin123"
echo ""
echo " To view logs: docker-compose logs -f"
echo "==================================="
