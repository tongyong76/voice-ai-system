#!/bin/bash

echo "==================================="
echo " Voice AI System - Stop Script"
echo "==================================="

echo "Stopping Docker services..."
docker-compose down

echo ""
echo "All services stopped."
echo "==================================="
