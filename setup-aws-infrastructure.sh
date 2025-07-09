#!/bin/bash
# AWS Infrastructure Setup Script
# Run this before deploying your application

set -e

echo "🏗️ Setting up AWS infrastructure for Spectrum Mental Health App..."

# Variables
APP_NAME="spectrum-mental-health"
REGION="us-east-1"
DB_NAME="spectrum_db"
DB_USERNAME="spectrum_admin"

# Check AWS CLI configuration
echo "🔍 Checking AWS CLI configuration..."
if ! aws sts get-caller-identity &> /dev/null; then
    echo "❌ AWS CLI not configured. Please run: aws configure"
    exit 1
fi

echo "✅ AWS CLI configured"

# Create S3 bucket for file storage (optional)
echo "📦 Creating S3 bucket for file storage..."
BUCKET_NAME="spectrum-app-files-$(date +%s)"
aws s3 mb s3://$BUCKET_NAME --region $REGION || echo "Bucket creation skipped"

# Create RDS PostgreSQL instance (optional - for production)
echo "🗄️ Setting up RDS PostgreSQL database..."
echo "Note: This will create a production database. Skip if using SQLite."
read -p "Create RDS PostgreSQL instance? (y/N): " create_rds

if [[ $create_rds =~ ^[Yy]$ ]]; then
    # Generate random password
    DB_PASSWORD=$(openssl rand -base64 32 | tr -d "=+/" | cut -c1-25)
    
    echo "Creating RDS instance..."
    aws rds create-db-instance \
        --db-instance-identifier spectrum-db \
        --db-instance-class db.t3.micro \
        --engine postgres \
        --engine-version 15.4 \
        --master-username $DB_USERNAME \
        --master-user-password $DB_PASSWORD \
        --allocated-storage 20 \
        --storage-type gp2 \
        --vpc-security-group-ids default \
        --backup-retention-period 7 \
        --storage-encrypted \
        --region $REGION
    
    echo "✅ RDS instance creation initiated"
    echo "📋 Database credentials:"
    echo "   Username: $DB_USERNAME"
    echo "   Password: $DB_PASSWORD"
    echo "   Save these credentials securely!"
    
    # Save credentials to file
    cat > aws-db-credentials.txt << EOF
Database Credentials for Spectrum Mental Health App
=================================================
RDS Instance: spectrum-db
Username: $DB_USERNAME
Password: $DB_PASSWORD
Region: $REGION

Connection String:
postgresql://$DB_USERNAME:$DB_PASSWORD@spectrum-db.XXXXXXXXXX.$REGION.rds.amazonaws.com:5432/$DB_NAME

⚠️  IMPORTANT: Keep these credentials secure!
EOF
    
    echo "📄 Credentials saved to aws-db-credentials.txt"
fi

# Create IAM role for Elastic Beanstalk (if needed)
echo "🔐 Checking IAM roles..."
if ! aws iam get-role --role-name aws-elasticbeanstalk-ec2-role &> /dev/null; then
    echo "Creating IAM role for Elastic Beanstalk..."
    # Note: This requires specific IAM permissions
    echo "⚠️  Please create IAM roles manually in AWS Console if needed"
fi

# Create security group for the application
echo "🛡️ Setting up security groups..."
VPC_ID=$(aws ec2 describe-vpcs --filters "Name=isDefault,Values=true" --query "Vpcs[0].VpcId" --output text --region $REGION)

if [ "$VPC_ID" != "None" ]; then
    # Create security group
    SG_ID=$(aws ec2 create-security-group \
        --group-name spectrum-app-sg \
        --description "Security group for Spectrum Mental Health App" \
        --vpc-id $VPC_ID \
        --region $REGION \
        --query "GroupId" --output text 2>/dev/null || echo "exists")
    
    if [ "$SG_ID" != "exists" ]; then
        # Add HTTP and HTTPS rules
        aws ec2 authorize-security-group-ingress \
            --group-id $SG_ID \
            --protocol tcp \
            --port 80 \
            --cidr 0.0.0.0/0 \
            --region $REGION
            
        aws ec2 authorize-security-group-ingress \
            --group-id $SG_ID \
            --protocol tcp \
            --port 443 \
            --cidr 0.0.0.0/0 \
            --region $REGION
            
        echo "✅ Security group created: $SG_ID"
    fi
fi

echo ""
echo "🎉 AWS infrastructure setup completed!"
echo ""
echo "📋 Next steps:"
echo "   1. Wait for RDS instance to be available (if created)"
echo "   2. Update .env.production with your database URL"
echo "   3. Run ./deploy-aws.sh to deploy your application"
echo "   4. Configure SSL certificate in AWS Certificate Manager"
echo "   5. Set up domain name in Route 53"
echo ""
echo "💡 Useful AWS commands:"
echo "   aws rds describe-db-instances --db-instance-identifier spectrum-db"
echo "   aws s3 ls s3://$BUCKET_NAME"
echo "   aws elasticbeanstalk describe-environments"
