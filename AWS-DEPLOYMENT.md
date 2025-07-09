# AWS Deployment Guide for Spectrum Mental Health App

## 🚀 Deployment Overview

This guide will help you deploy your Spectrum Mental Health Patient Management System to AWS using Elastic Beanstalk.

## 📋 Prerequisites

1. **AWS Account** - with appropriate permissions
2. **AWS CLI** - installed and configured
3. **EB CLI** - Elastic Beanstalk CLI
4. **Domain Name** - (optional but recommended)

## 🛠️ Setup Steps

### 1. Install Required Tools

```bash
# Install AWS CLI
# Windows: Download from https://aws.amazon.com/cli/
# macOS: brew install awscli
# Linux: pip install awscli

# Install EB CLI
pip install awsebcli

# Configure AWS CLI
aws configure
```

### 2. Prepare Your Application

```bash
# Make deployment scripts executable (on macOS/Linux)
chmod +x setup-aws-infrastructure.sh
chmod +x deploy-aws.sh

# Copy production environment file
cp .env.production .env
# Edit .env with your production values
```

### 3. Set Up AWS Infrastructure

```bash
# Run infrastructure setup (optional)
./setup-aws-infrastructure.sh
```

### 4. Deploy to AWS

```bash
# Deploy your application
./deploy-aws.sh
```

## 🔧 Configuration Files Explained

### Docker Configuration
- `Dockerfile` - Container configuration for your app
- `docker-compose.yml` - Local development with Docker

### AWS Configuration
- `.ebextensions/python.config` - Elastic Beanstalk configuration
- `.env.production` - Production environment variables

### Deployment Scripts
- `setup-aws-infrastructure.sh` - Sets up RDS, S3, security groups
- `deploy-aws.sh` - Deploys your application to Elastic Beanstalk

## 🏗️ AWS Architecture

Your deployed application will use:

- **Elastic Beanstalk** - Application hosting and auto-scaling
- **Application Load Balancer** - Traffic distribution and SSL termination
- **EC2 Instances** - Application servers
- **RDS PostgreSQL** - Production database (optional)
- **S3** - File storage (optional)
- **CloudWatch** - Monitoring and logging
- **Route 53** - DNS management (if using custom domain)
- **Certificate Manager** - SSL certificates

## 🔒 Security & HIPAA Compliance

### Production Security Features:
- ✅ HTTPS enforcement
- ✅ Security headers middleware
- ✅ Non-root Docker user
- ✅ Environment variable secrets
- ✅ Database encryption at rest
- ✅ Audit logging
- ✅ No debug endpoints in production

### HIPAA Compliance Features:
- ✅ PHI data encryption
- ✅ Access logging and audit trails
- ✅ User authentication and authorization
- ✅ Secure session management
- ✅ Data backup and retention policies

## 📊 Monitoring and Maintenance

### Health Monitoring
- Application health check at `/health`
- CloudWatch metrics and alarms
- Log aggregation and analysis

### Backup Strategy
- Automated RDS backups (7-day retention)
- Application configuration backups
- User file backups to S3

### Updates and Maintenance
```bash
# Deploy updates
eb deploy

# View logs
eb logs

# Check status
eb status

# SSH into server (for debugging)
eb ssh
```

## 💰 Cost Estimation

### Basic Setup (t3.micro)
- Elastic Beanstalk: Free tier eligible
- EC2 t3.micro: ~$8-15/month
- RDS t3.micro: ~$15-25/month
- Application Load Balancer: ~$20/month
- **Total: ~$43-60/month**

### Production Setup (t3.small)
- EC2 t3.small: ~$15-30/month
- RDS t3.small: ~$30-50/month
- Application Load Balancer: ~$20/month
- S3 Storage: ~$5-10/month
- **Total: ~$70-110/month**

## 🌐 Custom Domain Setup

1. **Purchase domain** in Route 53 or transfer existing domain
2. **Request SSL certificate** in Certificate Manager
3. **Configure CNAME** record pointing to EB environment
4. **Update allowed origins** in production environment

## 🚨 Troubleshooting

### Common Issues:

1. **Deployment fails**
   - Check EB logs: `eb logs`
   - Verify environment variables
   - Check application health endpoint

2. **Database connection issues**
   - Verify RDS security group allows EB access
   - Check database credentials
   - Ensure RDS instance is running

3. **File upload issues**
   - Check S3 bucket permissions
   - Verify upload directory exists
   - Check file size limits

### Useful Commands:
```bash
# View environment status
eb status

# Check application logs
eb logs --all

# Open EB console
eb console

# Restart application
eb deploy --staged

# Terminate environment (careful!)
eb terminate
```

## 📞 Support

For deployment issues:
1. Check AWS CloudWatch logs
2. Review Elastic Beanstalk events
3. Check application health endpoint
4. Review security group configurations

## 🔄 CI/CD Pipeline (Future Enhancement)

Consider setting up automated deployment with:
- GitHub Actions
- AWS CodePipeline
- Automated testing
- Blue-green deployments

---

**⚠️ Important Notes:**
- Always test in a staging environment first
- Keep your `.env` file secure and never commit it
- Regularly update dependencies for security
- Monitor costs and set up billing alerts
- Follow HIPAA compliance guidelines for patient data
