# Render.com Deployment Guide

This guide will help you deploy the ChatGPT Bridge API to Render.com.

## Prerequisites

- GitHub account
- Render.com account (free tier available)
- Your code pushed to a GitHub repository

---

## Deployment Steps

### 1. Push Your Code to GitHub

```bash
# Initialize git if not already done
git init

# Add all files
git add .

# Commit
git commit -m "Prepare for Render deployment"

# Add your GitHub repository as remote
git remote add origin https://github.com/yourusername/your-repo.git

# Push to GitHub
git push -u origin main
```

### 2. Create a New Web Service on Render

1. Go to [Render Dashboard](https://dashboard.render.com/)
2. Click **"New +"** → **"Web Service"**
3. Connect your GitHub repository
4. Configure the service:

**Basic Settings:**
- **Name**: `ccgpt-web` (or your preferred name)
- **Region**: Choose closest to your users
- **Branch**: `main`
- **Runtime**: `Python 3`
- **Build Command**: `./build.sh`
- **Start Command**: `daphne -b 0.0.0.0 -p $PORT config.asgi:application`

**Instance Type:**
- Select **Free** tier (or paid if needed)

### 3. Add Environment Variables

In the Render dashboard, add these environment variables:

#### Required Variables:

```
SECRET_KEY=<generate-a-strong-secret-key>
DEBUG=False
ALLOWED_HOSTS=<your-render-app-name>.onrender.com
```

#### Optional Variables:

```
CORS_ALLOWED_ORIGINS=https://your-frontend-domain.com
```

**To generate a SECRET_KEY:**
```python
python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
```

### 4. Create PostgreSQL Database

1. In Render Dashboard, click **"New +"** → **"PostgreSQL"**
2. Configure:
   - **Name**: `ccgpt-db`
   - **Database**: `ccgpt`
   - **User**: `ccgpt_user`
   - **Region**: Same as your web service
   - **Plan**: Free

3. After creation, copy the **Internal Database URL**

4. Go back to your Web Service → **Environment**
5. Add environment variable:
   ```
   DATABASE_URL=<paste-internal-database-url>
   ```

### 5. Create Redis Instance

1. In Render Dashboard, click **"New +"** → **"Redis"**
2. Configure:
   - **Name**: `ccgpt-redis`
   - **Region**: Same as your web service
   - **Plan**: Free (25MB)
   - **Maxmemory Policy**: `noeviction`

3. After creation, copy the **Internal Redis URL**

4. Go back to your Web Service → **Environment**
5. Add environment variable:
   ```
   REDIS_URL=<paste-internal-redis-url>
   ```

### 6. Deploy

1. Click **"Create Web Service"** or **"Manual Deploy"**
2. Wait for the build to complete (5-10 minutes)
3. Your app will be available at: `https://your-app-name.onrender.com`

---

## Post-Deployment Setup

### 1. Create Superuser

Access the Render Shell:

1. Go to your Web Service in Render Dashboard
2. Click **"Shell"** tab
3. Run:
```bash
python manage.py createsuperuser
```

Follow the prompts to create your admin account.

### 2. Access Admin Panel

Visit: `https://your-app-name.onrender.com/admin/`

### 3. Create API Accounts

1. Log in to admin panel
2. Go to **GPT Accounts**
3. Click **"Add GPT Account"**
4. Fill in:
   - Email
   - API Key (generate a secure random string)
   - Webhook URL (your callback endpoint)
   - Is Active: ✓

### 4. Test API

Visit Swagger UI: `https://your-app-name.onrender.com/api/docs/`

---

## Environment Variables Reference

### Required

| Variable | Description | Example |
|----------|-------------|---------|
| `SECRET_KEY` | Django secret key | `django-insecure-abc123...` |
| `DEBUG` | Debug mode | `False` |
| `DATABASE_URL` | PostgreSQL connection string | `postgresql://user:pass@host/db` |
| `REDIS_URL` | Redis connection string | `redis://host:port` |

### Optional

| Variable | Description | Example |
|----------|-------------|---------|
| `ALLOWED_HOSTS` | Comma-separated allowed hosts | `myapp.onrender.com,example.com` |
| `CORS_ALLOWED_ORIGINS` | Comma-separated CORS origins | `https://example.com,https://app.com` |

---

## Monitoring & Logs

### View Logs

1. Go to your Web Service in Render Dashboard
2. Click **"Logs"** tab
3. View real-time logs

### Monitor Performance

1. Go to **"Metrics"** tab
2. View:
   - CPU usage
   - Memory usage
   - Request count
   - Response times

---

## Troubleshooting

### Build Fails

**Check build logs:**
- Ensure `build.sh` is executable: `chmod +x build.sh`
- Verify all dependencies in `requirements.txt`
- Check Python version compatibility

**Common fixes:**
```bash
# Make build script executable
chmod +x build.sh
git add build.sh
git commit -m "Make build script executable"
git push
```

### Database Connection Issues

**Verify:**
- `DATABASE_URL` is set correctly
- Database is in the same region as web service
- Use **Internal Database URL** (not external)

### Redis Connection Issues

**Verify:**
- `REDIS_URL` is set correctly
- Redis instance is running
- Use **Internal Redis URL** (not external)

### Static Files Not Loading

**Check:**
- `collectstatic` runs in build script
- WhiteNoise is in `MIDDLEWARE`
- `STATIC_ROOT` is set correctly

### WebSocket Connection Fails

**Verify:**
- Daphne is running (check start command)
- WebSocket URL uses `wss://` (not `ws://`)
- CORS settings allow WebSocket connections

---

## Scaling

### Upgrade Instance

1. Go to your Web Service
2. Click **"Settings"**
3. Change **Instance Type** to a paid plan
4. Click **"Save Changes"**

### Add More Instances

1. Go to **"Settings"**
2. Increase **Number of Instances**
3. Click **"Save Changes"**

### Database Scaling

1. Go to your PostgreSQL database
2. Click **"Settings"**
3. Upgrade to a paid plan for more storage/connections

---

## Custom Domain

### Add Custom Domain

1. Go to your Web Service
2. Click **"Settings"**
3. Scroll to **"Custom Domain"**
4. Click **"Add Custom Domain"**
5. Enter your domain: `api.yourdomain.com`
6. Add the provided CNAME record to your DNS:
   ```
   CNAME: api.yourdomain.com → your-app.onrender.com
   ```
7. Wait for DNS propagation (5-30 minutes)
8. Render will automatically provision SSL certificate

### Update Environment Variables

After adding custom domain:
```
ALLOWED_HOSTS=api.yourdomain.com,your-app.onrender.com
```

---

## Backup & Restore

### Database Backup

Render automatically backs up PostgreSQL databases on paid plans.

**Manual backup:**
1. Go to your PostgreSQL database
2. Click **"Backups"** tab
3. Click **"Create Backup"**

**Restore from backup:**
1. Go to **"Backups"** tab
2. Find the backup
3. Click **"Restore"**

### Export Database

```bash
# From Render Shell
pg_dump $DATABASE_URL > backup.sql
```

---

## Cost Optimization

### Free Tier Limits

- **Web Service**: Spins down after 15 minutes of inactivity
- **PostgreSQL**: 90 days, then deleted if inactive
- **Redis**: 25MB storage, 30 days retention

### Keep Service Active

Use a service like [UptimeRobot](https://uptimerobot.com/) to ping your app every 5 minutes.

### Upgrade When Needed

Consider upgrading if you need:
- No spin-down (always-on)
- More resources (CPU/RAM)
- More database storage
- Longer Redis retention

---

## Security Best Practices

1. **Never commit secrets** - Use environment variables
2. **Use strong SECRET_KEY** - Generate a new one for production
3. **Set DEBUG=False** - Always in production
4. **Enable HTTPS only** - Render provides free SSL
5. **Restrict CORS** - Only allow trusted origins
6. **Regular updates** - Keep dependencies updated
7. **Monitor logs** - Check for suspicious activity
8. **Backup database** - Regular backups on paid plans

---

## CI/CD

### Auto-Deploy on Push

Render automatically deploys when you push to your main branch.

**Disable auto-deploy:**
1. Go to **"Settings"**
2. Uncheck **"Auto-Deploy"**
3. Use **"Manual Deploy"** button instead

### Deploy Specific Branch

1. Go to **"Settings"**
2. Change **"Branch"** to your desired branch
3. Click **"Save Changes"**

---

## Support

- **Render Docs**: https://render.com/docs
- **Render Community**: https://community.render.com/
- **Django Docs**: https://docs.djangoproject.com/
- **Channels Docs**: https://channels.readthedocs.io/

---

## Quick Reference

### Useful Commands (Render Shell)

```bash
# Run migrations
python manage.py migrate

# Create superuser
python manage.py createsuperuser

# Collect static files
python manage.py collectstatic --no-input

# Django shell
python manage.py shell

# Check deployment
python manage.py check --deploy
```

### URLs After Deployment

- **Homepage**: `https://your-app.onrender.com/`
- **Admin**: `https://your-app.onrender.com/admin/`
- **API Docs**: `https://your-app.onrender.com/api/docs/`
- **ReDoc**: `https://your-app.onrender.com/api/redoc/`
- **API Schema**: `https://your-app.onrender.com/api/schema/`

---

## Next Steps

1. ✅ Deploy to Render
2. ✅ Create superuser
3. ✅ Create API accounts
4. ✅ Test API endpoints
5. ✅ Set up monitoring
6. ✅ Configure custom domain (optional)
7. ✅ Set up backups (paid plans)
8. ✅ Develop browser extension
9. ✅ Integrate with your application

---

**Congratulations! Your ChatGPT Bridge API is now live on Render.com! 🎉**
