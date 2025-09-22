# Imagefeed Manager (Django)

Prototype for managing frame overlays and processing product images from a feed. Not affiliated with academic or professional work.

## Features

- **Auth**: Django sessions and login
- **Frames**: Upload JPG frames and tune overlay coordinates with live preview
- **Processing**: Bulk image generation with Celery (optional)
- **Management**: Paginated views for outputs
- **Health**: Simple health endpoints

## Requirements

- Python 3.8+
- Redis (only if you run Celery)

## Quick Start

```bash
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt

python manage.py migrate
python manage.py createsuperuser

# Optional workers
# Terminal 1: Redis
# redis-server

# Terminal 2: Celery worker
# celery -A project worker --loglevel=info

# App server
python manage.py runserver
```

Key URLs
- Dashboard: /
- Admin: /admin/

## Configuration

Set environment variables as needed (examples):
```bash
SECRET_KEY=changeme
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1
REDIS_URL=redis://localhost:6379/0
```

## Deploy (summary)

- Set `DEBUG=False`, a strong `SECRET_KEY`, and proper `ALLOWED_HOSTS`
- Run `python manage.py collectstatic`
- Use a real database (e.g., Postgres) and a production-ready web server

## Troubleshooting (short)

- Celery not processing: ensure Redis is running and the worker is started
- PIL errors: verify Pillow installation and media permissions

## License

MIT