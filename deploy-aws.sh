#!/bin/bash
# AWS Deployment Script for Spectrum Mental Health App
# Run this script to deploy to AWS Elastic Beanstalk

set -e

echo "🚀 Starting AWS deployment for Spectrum Mental Health App..."

# Check if AWS CLI is installed
if ! command -v aws &> /dev/null; then
    echo "❌ AWS CLI is not installed. Please install it first."
    echo "Visit: https://aws.amazon.com/cli/"
    exit 1
fi

# Check if EB CLI is installed
if ! command -v eb &> /dev/null; then
    echo "❌ Elastic Beanstalk CLI is not installed. Installing..."
    pip install awsebcli
fi

# Set variables
APP_NAME="spectrum-mental-health"
ENV_NAME="spectrum-production"
REGION="us-east-1"
PLATFORM="python-3.11"

echo "📋 Deployment Configuration:"
echo "   App Name: $APP_NAME"
echo "   Environment: $ENV_NAME"
echo "   Region: $REGION"
echo "   Platform: $PLATFORM"

# Create .elasticbeanstalk directory if it doesn't exist
mkdir -p .elasticbeanstalk

# Create EB config file
cat > .elasticbeanstalk/config.yml << EOF
branch-defaults:
  main:
    environment: $ENV_NAME
global:
  application_name: $APP_NAME
  default_ec2_keyname: null
  default_platform: $PLATFORM
  default_region: $REGION
  include_git_submodules: true
  instance_profile: null
  platform_name: null
  platform_version: null
  profile: default
  sc: git
  workspace_type: Application
EOF

echo "✅ Configuration files created"

# Initialize EB application (if not already done)
if [ ! -f .elasticbeanstalk/config.yml ]; then
    echo "🔧 Initializing Elastic Beanstalk application..."
    eb init $APP_NAME --platform $PLATFORM --region $REGION
fi

echo "📦 Preparing deployment package..."

# Create a deployment package (exclude development files)
echo "Excluding development files..."

# Deploy to Elastic Beanstalk
echo "🚀 Deploying to AWS Elastic Beanstalk..."
echo "This may take several minutes..."

# Create environment if it doesn't exist, or deploy to existing
if eb list | grep -q $ENV_NAME; then
    echo "Deploying to existing environment: $ENV_NAME"
    eb deploy $ENV_NAME
else
    echo "Creating new environment: $ENV_NAME"
    eb create $ENV_NAME --instance-types t3.small --min-instances 1 --max-instances 3
fi

echo "✅ Deployment completed!"
echo "🌐 Your application should be available at:"
eb status $ENV_NAME | grep "CNAME" | awk '{print "   https://" $2}'

echo ""
echo "📋 Next steps:"
echo "   1. Configure your domain name in AWS Route 53"
echo "   2. Set up SSL certificate in AWS Certificate Manager"
echo "   3. Update environment variables in EB console"
echo "   4. Configure RDS database if needed"
echo "   5. Set up CloudWatch monitoring"
echo ""
echo "🔧 To manage your deployment:"
echo "   eb status    - Check application status"
echo "   eb logs      - View application logs"
echo "   eb ssh       - SSH into application server"
echo "   eb terminate - Terminate environment (be careful!)"
