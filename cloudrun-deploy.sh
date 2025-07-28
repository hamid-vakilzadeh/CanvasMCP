#!/bin/bash

# Cloud Run deployment script for Canvas MCP
# Usage: ./cloudrun-deploy.sh [PROJECT_ID] [SERVICE_NAME] [REGION]

PROJECT_ID=${1:-"victor-adf28"}
SERVICE_NAME=${2:-"canvas-mcp"}
REGION=${3:-"us-central1"}

echo "Deploying Canvas MCP to Google Cloud Run..."
echo "Project ID: $PROJECT_ID"
echo "Service Name: $SERVICE_NAME"
echo "Region: $REGION"

# Enable Secret Manager API if not already enabled
gcloud services enable secretmanager.googleapis.com --project=$PROJECT_ID

# Build and deploy to Cloud Run from source
gcloud run deploy $SERVICE_NAME \
  --source . \
  --platform managed \
  --region $REGION \
  --project $PROJECT_ID \
  --allow-unauthenticated \
  --port 3000 \
  --memory 512Mi \
  --cpu 1 \
  --max-instances 10 \
  --service-account "canvas-mcp-sa@$PROJECT_ID.iam.gserviceaccount.com" \
  --set-env-vars "MCP_TRANSPORT=http,MCP_HOST=0.0.0.0,MCP_PORT=3000,MCP_PATH=/mcp" \
  --set-secrets "ENCRYPTION_SECRET=ENCRYPTION_SECRET:latest"

echo "Deployment complete!"
echo "Your MCP server will be available at:"
gcloud run services describe $SERVICE_NAME --region=$REGION --project=$PROJECT_ID --format="value(status.url)"