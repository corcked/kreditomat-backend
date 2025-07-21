# Backend Deployment Guide

## Railway Deployment

### Prerequisites
- Railway account
- Railway CLI installed (optional)
- PostgreSQL database (provided by Railway)
- Redis instance (provided by Railway)

### Environment Variables

Set these in Railway dashboard:

```env
# Database (auto-provided by Railway PostgreSQL)
DATABASE_URL=postgresql://user:password@host:port/dbname

# Redis (auto-provided by Railway Redis)
REDIS_URL=redis://default:password@host:port

# Security
SECRET_KEY=your-secret-key-here
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=60

# Telegram Gateway (for production)
TELEGRAM_BOT_TOKEN=your-bot-token
USE_TELEGRAM_TEST_DC=false

# Environment
ENVIRONMENT=production
DEBUG=false

# Frontend URL (for CORS)
FRONTEND_URL=https://your-frontend.railway.app
```

### Deployment Steps

#### Via Railway Dashboard

1. Create new project in Railway
2. Add PostgreSQL service
3. Add Redis service
4. Connect your GitHub repository
5. Select the `kreditomat-backend` directory
6. Railway will auto-detect Python and use nixpacks
7. Set environment variables in Settings
8. Deploy

#### Via Railway CLI

```bash
# Install Railway CLI
npm install -g @railway/cli

# Login to Railway
railway login

# Initialize project
railway init

# Add services
railway service create postgres
railway service create redis

# Link to existing project (if needed)
railway link [project-id]

# Set environment variables
railway variables set SECRET_KEY=your-secret-key
railway variables set TELEGRAM_BOT_TOKEN=your-bot-token
railway variables set FRONTEND_URL=https://your-frontend.railway.app

# Deploy
railway up
```

### Docker Deployment (Alternative)

```bash
# Build image
docker build -t kreditomat-backend .

# Run locally with docker-compose
docker-compose up -d

# Run standalone
docker run -p 8000:8000 \
  -e DATABASE_URL=postgresql://... \
  -e REDIS_URL=redis://... \
  -e SECRET_KEY=... \
  kreditomat-backend
```

### Database Migrations

Migrations run automatically on deployment. To run manually:

```bash
# Via Railway CLI
railway run alembic upgrade head

# Via Docker
docker exec <container-id> alembic upgrade head
```

### Health Checks

The app includes health check endpoints:
- `/health` - Basic health check
- `/api/v1/health` - Detailed health with dependency checks

### Troubleshooting

#### Database Connection Issues
- Verify DATABASE_URL is set correctly
- Check if PostgreSQL service is running
- Ensure network connectivity between services

#### Redis Connection Issues
- Verify REDIS_URL is set correctly
- Check if Redis service is running
- Monitor Redis memory usage

#### Migration Failures
- Check database connectivity
- Review migration files for errors
- Run migrations manually to see detailed errors

#### Performance Issues
- Enable connection pooling in SQLAlchemy
- Monitor database query performance
- Check Redis cache hit rates
- Review Railway metrics dashboard

### SSL/HTTPS

Railway provides automatic SSL certificates. No additional configuration needed.

### Custom Domain

1. Add custom domain in Railway settings
2. Update DNS records as instructed
3. Update FRONTEND_URL for CORS

### Scaling

Railway automatically handles scaling. For manual control:
1. Go to service settings
2. Adjust instance size and count
3. Configure autoscaling rules

### Monitoring

1. Use Railway's built-in metrics
2. Set up external monitoring:
   - Sentry for error tracking
   - DataDog for APM
   - Custom Prometheus metrics

### Backup Strategy

#### Database Backups
```bash
# Manual backup via Railway CLI
railway run pg_dump $DATABASE_URL > backup.sql

# Restore
railway run psql $DATABASE_URL < backup.sql
```

#### Automated Backups
1. Enable Railway's automated backups
2. Configure backup schedule
3. Test restore procedures

### Rollback

Via Railway dashboard:
1. Go to deployments history
2. Click on previous successful deployment
3. Click "Redeploy"

Via CLI:
```bash
railway deployments
railway redeploy [deployment-id]
```

### Security Checklist

- [ ] Strong SECRET_KEY set
- [ ] DEBUG mode disabled
- [ ] HTTPS enforced
- [ ] CORS properly configured
- [ ] Rate limiting enabled
- [ ] Input validation active
- [ ] SQL injection protection
- [ ] Environment variables secured

### Performance Optimization

1. **Database**
   - Add appropriate indexes
   - Use connection pooling
   - Optimize queries

2. **Caching**
   - Redis for session storage
   - Cache frequently accessed data
   - Set appropriate TTLs

3. **API**
   - Enable response compression
   - Implement pagination
   - Use async operations

### Logs

View logs via Railway dashboard or CLI:

```bash
# Stream logs
railway logs

# View specific service logs
railway logs -s postgres
railway logs -s redis
```