#!/bin/bash
# Deploy Sequential Narrative AI to Google Cloud Run
# Usage: ./deploy.sh

set -e

# Configuration
PROJECT_ID="sequential-narrative-ai"
REGION="us-central1"
FRONTEND_SERVICE="narrative-ai-frontend"
BACKEND_SERVICE="narrative-ai-backend"

echo "============================================"
echo "🚀 Sequential Narrative AI - Cloud Run Deployment"
echo "============================================"
echo ""

# Check if gcloud is installed
if ! command -v gcloud &> /dev/null; then
    echo "❌ gcloud CLI not found. Please install: https://cloud.google.com/sdk/docs/install"
    exit 1
fi

# Check if user is authenticated
if ! gcloud auth print-identity-token &> /dev/null; then
    echo "🔐 Please authenticate with Google Cloud:"
    gcloud auth login
fi

# Set project
echo "📁 Setting project to: $PROJECT_ID"
gcloud config set project $PROJECT_ID

# Enable required APIs
echo "🔧 Enabling required APIs..."
gcloud services enable \
    cloudbuild.googleapis.com \
    run.googleapis.com \
    containerregistry.googleapis.com \
    secretmanager.googleapis.com \
    --quiet

# Check for required secrets
echo "🔑 Checking for API keys..."
echo ""
echo "Please ensure these secrets are set in Secret Manager or as environment variables:"
echo "  - OPENROUTER_API_KEY"
echo "  - TMDB_API_KEY"
echo "  - YOUTUBE_API_KEY"
echo ""

# Prompt for API keys if not in environment
if [ -z "$OPENROUTER_API_KEY" ]; then
    read -p "Enter OPENROUTER_API_KEY: " OPENROUTER_API_KEY
fi

if [ -z "$TMDB_API_KEY" ]; then
    read -p "Enter TMDB_API_KEY: " TMDB_API_KEY
fi

if [ -z "$YOUTUBE_API_KEY" ]; then
    read -p "Enter YOUTUBE_API_KEY: " YOUTUBE_API_KEY
fi

# Build and deploy backend
echo ""
echo "📦 Building and deploying backend..."
cd backend

gcloud builds submit --tag gcr.io/$PROJECT_ID/$BACKEND_SERVICE

gcloud run deploy $BACKEND_SERVICE \
    --image gcr.io/$PROJECT_ID/$BACKEND_SERVICE \
    --region $REGION \
    --platform managed \
    --port 8888 \
    --memory 1Gi \
    --cpu 1 \
    --min-instances 0 \
    --max-instances 10 \
    --allow-unauthenticated \
    --set-env-vars "OPENROUTER_API_KEY=$OPENROUTER_API_KEY,TMDB_API_KEY=$TMDB_API_KEY,YOUTUBE_API_KEY=$YOUTUBE_API_KEY"

cd ..

# Get backend URL
BACKEND_URL=$(gcloud run services describe $BACKEND_SERVICE --region=$REGION --format='value(status.url)')
echo "✅ Backend deployed at: $BACKEND_URL"

# Build and deploy frontend
echo ""
echo "📦 Building and deploying frontend..."

gcloud builds submit \
    --tag gcr.io/$PROJECT_ID/$FRONTEND_SERVICE \
    --build-arg VITE_API_URL=$BACKEND_URL

gcloud run deploy $FRONTEND_SERVICE \
    --image gcr.io/$PROJECT_ID/$FRONTEND_SERVICE \
    --region $REGION \
    --platform managed \
    --port 80 \
    --memory 256Mi \
    --cpu 1 \
    --min-instances 0 \
    --max-instances 10 \
    --allow-unauthenticated

# Get frontend URL
FRONTEND_URL=$(gcloud run services describe $FRONTEND_SERVICE --region=$REGION --format='value(status.url)')

# Print summary
echo ""
echo "============================================"
echo "✅ Deployment Complete!"
echo "============================================"
echo ""
echo "🌐 Frontend: $FRONTEND_URL"
echo "⚙️  Backend:  $BACKEND_URL"
echo ""
echo "📊 View in Cloud Console:"
echo "   https://console.cloud.google.com/run?project=$PROJECT_ID"
echo ""
echo "============================================"
