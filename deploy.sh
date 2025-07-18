#!/bin/bash

# Azure Container Apps deployment script
set -e

# Configuration variables
RESOURCE_GROUP="canvas-mcp-rg"
LOCATION="eastus"
CONTAINER_APP_ENV="canvas-mcp-env"
APP_NAME="canvas-mcp-app"
REGISTRY_NAME="canvasmcpregistry"
IMAGE_NAME="canvas-mcp"

# Set Canvas credentials from azure-deploy.yml
CANVAS_URL="https://uwwtw.instructure.com"
CANVAS_ACCESS_TOKEN="11830~2UYWcTf9Wy3xVDucc8L3nrYxGPCEBYn4XGQc2P4BFm4Pmuf2UR6MUDuC7vRwCYXH"

echo "Creating resource group..."
az group create --name $RESOURCE_GROUP --location $LOCATION

echo "Creating container registry..."
az acr create --resource-group $RESOURCE_GROUP --name $REGISTRY_NAME --sku Basic --admin-enabled true

echo "Building and pushing image..."
az acr build --registry $REGISTRY_NAME --image $IMAGE_NAME:latest .

echo "Creating container app environment..."
az containerapp env create --name $CONTAINER_APP_ENV --resource-group $RESOURCE_GROUP --location $LOCATION

echo "Deploying container app..."
az containerapp create \
  --name $APP_NAME \
  --resource-group $RESOURCE_GROUP \
  --environment $CONTAINER_APP_ENV \
  --image $REGISTRY_NAME.azurecr.io/$IMAGE_NAME:latest \
  --target-port 8000 \
  --ingress external \
  --min-replicas 1 \
  --max-replicas 1 \
  --cpu 0.5 \
  --memory 1Gi \
  --env-vars CANVAS_URL="$CANVAS_URL" CANVAS_ACCESS_TOKEN="$CANVAS_ACCESS_TOKEN"

echo "Getting app URL..."
APP_URL=$(az containerapp show --name $APP_NAME --resource-group $RESOURCE_GROUP --query properties.configuration.ingress.fqdn --output tsv)
echo "App deployed at: https://$APP_URL"

echo "Deployment complete!"
echo ""
echo "To connect from Claude Desktop, use this URL in your MCP configuration:"
echo "http://$APP_URL"