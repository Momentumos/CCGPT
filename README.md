# Django Project with Docker & PostgreSQL

A modern Django application with Docker, PostgreSQL, and REST API support.

## 🚀 Quick Start with Docker

### Prerequisites
- Docker
- Docker Compose

### 1. Clone and Setup
```bash
# Copy environment variables
cp .env.example .env

# Edit .env with your configuration (optional, defaults work for local development)
```

### 2. Build and Run
```bash
# Build and start all services
docker-compose up --build

# Or run in detached mode
docker-compose up -d --build
```

The application will be available at **http://localhost:8000**

### 3. Create Superuser
```bash
docker-compose exec web python manage.py createsuperuser
```

### 4. Common Docker Commands
```bash
# Stop services
docker-compose down

# View logs
docker-compose logs -f

# Run migrations
docker-compose exec web python manage.py migrate

# Create a new app
docker-compose exec web python manage.py startapp <app_name>

# Access Django shell
docker-compose exec web python manage.py shell

# Access PostgreSQL shell
docker-compose exec db psql -U django_user -d django_db
```

## 📁 Project Structure
```
.
├── config/              # Django project settings
├── Dockerfile           # Docker configuration for Django
├── docker-compose.yml   # Multi-container Docker setup
├── requirements.txt     # Python dependencies
├── .env                 # Environment variables (not in git)
├── .env.example         # Example environment variables
├── .gitignore          # Git ignore rules
├── .dockerignore       # Docker ignore rules
└── manage.py           # Django management script
```

## 🛠️ Technology Stack
- **Django 4.2 LTS** - Web framework
- **PostgreSQL 15** - Database
- **Django REST Framework** - API development
- **CORS Headers** - Cross-origin resource sharing
- **Docker & Docker Compose** - Containerization
- **python-decouple** - Environment variable management
- **Pillow** - Image processing

## 🔧 Environment Variables

Key environment variables in `.env`:

```env
SECRET_KEY=your-secret-key-here-change-this-in-production
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1

# PostgreSQL Database
DB_NAME=django_db
DB_USER=django_user
DB_PASSWORD=django_password
DB_HOST=db
DB_PORT=5432
```

**⚠️ Important:** Change `SECRET_KEY` and `DB_PASSWORD` in production!

## 📝 Development Workflow

### Create a New Django App
```bash
docker-compose exec web python manage.py startapp myapp
```

Then add it to `INSTALLED_APPS` in `config/settings.py`:
```python
INSTALLED_APPS = [
    # ...
    'myapp',
]
```

### Make and Apply Migrations
```bash
docker-compose exec web python manage.py makemigrations
docker-compose exec web python manage.py migrate
```

### Collect Static Files
```bash
docker-compose exec web python manage.py collectstatic --noinput
```

## 🧪 Running Tests
```bash
docker-compose exec web python manage.py test
```

## 🌐 API Development
Django REST Framework is pre-configured. Access the browsable API at:
- **http://localhost:8000/api/** (configure your URLs)

## 🔒 Production Deployment

For production:
1. Set `DEBUG=False` in `.env`
2. Generate a strong `SECRET_KEY`
3. Update `ALLOWED_HOSTS` with your domain
4. Use strong database credentials
5. Configure proper CORS settings
6. Set up a reverse proxy (nginx)
7. Use a production WSGI server (gunicorn)

## 🔌 System Architecture

This project implements a robust ChatGPT message queuing and processing system:

### Components
1. **REST API** - Clients submit messages with API key authentication
2. **Message Queue** - Requests are queued with states: idle → executing → done/failed
3. **WebSocket Server** - Real-time communication with browser extension
4. **Browser Extension** - Processes messages in ChatGPT and returns responses
5. **Webhook System** - Sends responses back to client's configured endpoint

### Request Flow
```
Client → API → Queue → WebSocket → Browser Extension → ChatGPT → Response → Webhook
```

### Features
- **API Key Authentication** - Secure access control
- **Request States** - Track message lifecycle (idle, executing, done, failed)
- **Response Types** - Support for thinking, auto, and instant modes
- **Thinking Time** - Standard or extended thinking duration
- **Chat Continuity** - Continue conversations with chat_id
- **Webhook Notifications** - Async response delivery
- **Real-time WebSocket** - Instant message delivery to extension

See [API_DOCUMENTATION.md](API_DOCUMENTATION.md) for complete API reference.

## 📚 Additional Resources
- [Django Documentation](https://docs.djangoproject.com/)
- [Django REST Framework](https://www.django-rest-framework.org/)
- [Django Channels](https://channels.readthedocs.io/)
- [Docker Documentation](https://docs.docker.com/)
- [PostgreSQL Documentation](https://www.postgresql.org/docs/)
- [Redis Documentation](https://redis.io/documentation)
