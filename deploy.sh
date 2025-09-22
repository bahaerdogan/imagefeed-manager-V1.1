

set -e

echo "🚀 Starting Django Frame Processor deployment..."

if [ ! -d "venv" ]; then
    echo "📦 Creating virtual environment..."
    python3 -m venv venv
fi

echo "🔧 Activating virtual environment..."
source venv/bin/activate

echo "📚 Installing dependencies..."
pip install -r requirements.txt

if [ ! -f ".env" ]; then
    echo "⚠️  Creating .env file from template..."
    cp .env.example .env
    echo "🔑 Please edit .env file with your production settings!"
fi

echo "🔒 Running security checks..."
python manage.py check --deploy

echo "📝 Creating logs directory..."
mkdir -p logs

echo "🗄️  Running database migrations..."
python manage.py migrate

echo "📁 Collecting static files..."
python manage.py collectstatic --noinput --clear

echo "🧪 Running tests..."
python manage.py test

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