#!/bin/bash

# Django Frame Processor Deployment Script
# This script sets up the application for production deployment

set -e

echo "🚀 Starting Django Frame Processor deployment..."

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "📦 Creating virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
echo "🔧 Activating virtual environment..."
source venv/bin/activate

# Install dependencies
echo "📚 Installing dependencies..."
pip install -r requirements.txt

# Check if .env file exists
if [ ! -f ".env" ]; then
    echo "⚠️  Creating .env file from template..."
    cp .env.example .env
    echo "🔑 Please edit .env file with your production settings!"
fi

# Run security checks
echo "🔒 Running security checks..."
python manage.py check --deploy

# Create logs directory
echo "📝 Creating logs directory..."
mkdir -p logs

# Run database migrations
echo "🗄️  Running database migrations..."
python manage.py migrate

# Collect static files (if needed for production)
echo "📁 Collecting static files..."
python manage.py collectstatic --noinput --clear

# Run tests
echo "🧪 Running tests..."
python manage.py test

# Create superuser (interactive)
echo "👤 Creating superuser (optional)..."
read -p "Do you want to create a superuser? (y/n): " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    python manage.py createsuperuser
fi

echo "✅ Deployment completed successfully!"
echo ""
echo "📋 Next steps:"
echo "1. Edit .env file with your production settings"
echo "2. Start Redis server: redis-server"
echo "3. Start Celery worker: celery -A project worker --loglevel=info"
echo "4. Start Django server: python manage.py runserver"
echo ""
echo "🔗 Health check endpoints:"
echo "- Basic: http://localhost:8000/health/"
echo "- Database: http://localhost:8000/health/db/"
echo "- Redis: http://localhost:8000/health/redis/"
echo ""
echo "🎉 Happy coding!"