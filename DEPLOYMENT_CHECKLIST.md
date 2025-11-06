# Deployment Checklist

## Pre-Deployment

- [ ] All code committed to Git
- [ ] `.env` file is in `.gitignore` (✓ already done)
- [ ] `SECRET_KEY` is not hardcoded in settings.py
- [ ] `DEBUG=False` for production
- [ ] All dependencies in `requirements.txt`
- [ ] `build.sh` is executable (`chmod +x build.sh`)
- [ ] Code pushed to GitHub

## Render Setup

### 1. Create Services

- [ ] PostgreSQL database created
- [ ] Redis instance created
- [ ] Web service created

### 2. Environment Variables

- [ ] `SECRET_KEY` - Generated or set
- [ ] `DEBUG` - Set to `False`
- [ ] `DATABASE_URL` - Connected from database
- [ ] `REDIS_URL` - Connected from Redis
- [ ] `ALLOWED_HOSTS` - Set to your Render domain (optional, auto-detected)
- [ ] `CORS_ALLOWED_ORIGINS` - Set if needed

### 3. Deploy

- [ ] Initial deployment successful
- [ ] Build logs checked for errors
- [ ] Application is accessible

## Post-Deployment

### 4. Database Setup

- [ ] Migrations ran successfully (automatic in build.sh)
- [ ] Superuser created via Render Shell
- [ ] Admin panel accessible

### 5. Testing

- [ ] Admin login works: `/admin/`
- [ ] API docs accessible: `/api/docs/`
- [ ] Create test GPT Account in admin
- [ ] Test API endpoint with Swagger UI
- [ ] WebSocket connection works

### 6. Configuration

- [ ] GPT Accounts created with API keys
- [ ] Webhook URLs configured
- [ ] CORS settings verified

### 7. Monitoring

- [ ] Logs are being generated
- [ ] Metrics are visible in Render dashboard
- [ ] Health checks passing

## Optional

- [ ] Custom domain configured
- [ ] DNS records updated
- [ ] SSL certificate provisioned (automatic)
- [ ] Uptime monitoring set up (UptimeRobot, etc.)
- [ ] Error tracking configured (Sentry, etc.)
- [ ] Backup strategy implemented

## Security Verification

- [ ] `DEBUG=False` in production
- [ ] HTTPS enforced (automatic on Render)
- [ ] CORS properly configured
- [ ] API keys are secure and random
- [ ] No secrets in Git repository
- [ ] Admin panel accessible only with strong password

## Performance

- [ ] Static files loading correctly
- [ ] Database queries optimized
- [ ] Redis connection working
- [ ] WebSocket connections stable
- [ ] Response times acceptable

## Documentation

- [ ] API documentation accessible
- [ ] README updated with production URL
- [ ] Team members have access credentials
- [ ] Deployment process documented

---

## Quick Commands

### Access Render Shell
```bash
# In Render Dashboard → Shell tab
python manage.py createsuperuser
python manage.py migrate
python manage.py collectstatic --no-input
```

### Test Locally Before Deploy
```bash
# Set production-like environment
export DEBUG=False
export SECRET_KEY=test-key
export DATABASE_URL=postgresql://...
export REDIS_URL=redis://...

# Run checks
python manage.py check --deploy
python manage.py collectstatic --no-input
python manage.py migrate

# Test server
daphne -b 0.0.0.0 -p 8000 config.asgi:application
```

### Generate SECRET_KEY
```python
python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
```

---

## Troubleshooting

### Build Fails
- Check `build.sh` is executable
- Verify all dependencies in `requirements.txt`
- Check build logs for specific errors

### Database Connection Error
- Verify `DATABASE_URL` is set
- Check database is in same region
- Use internal database URL

### Static Files Not Loading
- Check `collectstatic` ran in build
- Verify WhiteNoise is configured
- Check `STATIC_ROOT` setting

### WebSocket Connection Fails
- Use `wss://` (not `ws://`) for production
- Check Daphne is running
- Verify Redis connection

---

## Support Resources

- [Render Documentation](https://render.com/docs)
- [Django Deployment Checklist](https://docs.djangoproject.com/en/4.2/howto/deployment/checklist/)
- [Channels Deployment](https://channels.readthedocs.io/en/stable/deploying.html)
- [RENDER_DEPLOYMENT.md](./RENDER_DEPLOYMENT.md) - Detailed guide

---

**Status**: Ready for deployment! 🚀
