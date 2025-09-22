# Django Görsel İşleme & Feed Yönetim Uygulaması

Production-ready Django application for processing XML feeds and overlaying product images onto frame templates.

## Features

- **Secure Authentication**: Django built-in authentication with session management
- **Frame Project Management**: Upload JPG frame images and configure XML feed URLs
- **Real-time Preview**: Interactive coordinate adjustment with live preview
- **Bulk Image Processing**: Asynchronous processing using Celery for all feed products
- **Data Management**: Server-side paginated DataTables for output management
- **Health Monitoring**: Built-in health check endpoints
- **Security**: SSRF protection, file upload validation, rate limiting

## Architecture

- **Backend**: Django 4.2+ with PostgreSQL/SQLite
- **Cache & Queue**: Redis for caching and Celery task queue
- **Image Processing**: Pillow with optimization and security validation
- **Frontend**: Bootstrap 5 + jQuery + DataTables
- **Monitoring**: Structured logging with rotation

## Quick Start

### Prerequisites
- Python 3.8+
- Redis server
- Virtual environment (recommended)

### Installation

1. **Clone and setup environment**
```bash
git clone <repository-url>
cd django-frame-processor
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

2. **Install dependencies**
```bash
pip install -r requirements.txt
```

3. **Configure environment**
```bash
cp .env.example .env
# Edit .env with your settings
```

4. **Setup database**
```bash
python manage.py migrate
python manage.py createsuperuser
```

5. **Start services**
```bash
# Terminal 1: Redis
redis-server

# Terminal 2: Celery Worker
celery -A project worker --loglevel=info

# Terminal 3: Django Server
python manage.py runserver
```

## Production Deployment

### Environment Variables
```bash
SECRET_KEY=your-production-secret-key
DEBUG=False
ALLOWED_HOSTS=yourdomain.com
DATABASE_URL=postgresql://user:pass@localhost/dbname
REDIS_URL=redis://localhost:6379/0
```

### Security Checklist
- [ ] Set strong SECRET_KEY
- [ ] Configure HTTPS (SSL certificates)
- [ ] Set up proper firewall rules
- [ ] Configure rate limiting
- [ ] Set up monitoring and alerting
- [ ] Regular security updates

### Performance Optimization
- [ ] Configure Redis for production
- [ ] Set up database connection pooling
- [ ] Configure static file serving (nginx/Apache)
- [ ] Set up CDN for media files
- [ ] Configure Celery with proper concurrency

## API Endpoints

### Health Checks
- `GET /health/` - Basic health check
- `GET /health/db/` - Database connectivity
- `GET /health/redis/` - Redis connectivity

### Application
- `GET /` - Dashboard
- `GET /frames/` - Frame list
- `POST /frames/create/` - Create new frame
- `GET /frames/{id}/preview/` - Preview and coordinate adjustment
- `POST /frames/{id}/preview-image/` - Generate preview image
- `GET /frames/{id}/outputs-data/` - DataTable data endpoint

## Security Features

### SSRF Protection
- URL validation against private IP ranges
- Blocked dangerous ports
- Request timeout limits
- Content-type validation

### File Upload Security
- File size limits (10MB)
- Extension validation (JPG/JPEG only)
- Content validation using PIL
- Sanitized file names

### Input Validation
- Coordinate boundary checking
- SQL injection prevention
- XSS protection with Django templates
- CSRF protection

## Monitoring & Logging

### Log Files
- `logs/django.log` - Application logs with rotation
- Structured logging with timestamps and context

### Metrics to Monitor
- Response times
- Error rates
- Queue length (Celery)
- Memory usage
- Disk space (media files)

## Development

### Code Quality
- Type hints where applicable
- Comprehensive error handling
- Database indexes for performance
- Transaction management
- Caching strategy

### Testing
```bash
python manage.py test
python manage.py check --deploy  # Production readiness check
```

### Database Migrations
```bash
python manage.py makemigrations
python manage.py migrate
```

## Troubleshooting

### Common Issues

**Celery tasks not processing:**
- Check Redis connection
- Verify Celery worker is running
- Check task queue: `celery -A project inspect active`

**Image processing errors:**
- Verify PIL/Pillow installation
- Check file permissions in media directory
- Validate image URLs are accessible

**Performance issues:**
- Monitor database query count
- Check Redis memory usage
- Review Celery concurrency settings

### Debug Mode
```bash
DEBUG=True python manage.py runserver
```

## Contributing

1. Follow PEP 8 style guidelines
2. Add tests for new features
3. Update documentation
4. Use meaningful commit messages

## License

This project is licensed under the MIT License.