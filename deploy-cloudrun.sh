#!/bin/bash
# =============================================================
# deploy-cloudrun.sh — Deploy no Google Cloud Run
# =============================================================

set -e

PROJECT_ID="deploy-agent-om"
REGION="europe-west1"
APP_NAME="rag-grupo-om"
SERVICE_ACCOUNT="rag-grupo-om-sa@deploy-agent-om.iam.gserviceaccount.com"

AR_REPO="$REGION-docker.pkg.dev/$PROJECT_ID/$APP_NAME"
BACKEND_IMAGE="$AR_REPO/backend:latest"
FRONTEND_IMAGE="$AR_REPO/frontend:latest"

# =============================================================
# PASSO 1 — Habilita APIs (só na primeira vez)
# =============================================================
echo "🔧 Habilitando APIs do Google Cloud..."
gcloud services enable \
  artifactregistry.googleapis.com \
  run.googleapis.com \
  --project=$PROJECT_ID

# =============================================================
# PASSO 2 — Cria repositório no Artifact Registry (só na primeira vez)
# =============================================================
echo "📦 Criando repositório no Artifact Registry..."
gcloud artifacts repositories create $APP_NAME \
  --repository-format=docker \
  --location=$REGION \
  --description="Imagens Docker do $APP_NAME" \
  --project=$PROJECT_ID || echo "Repositório já existe, continuando..."

# =============================================================
# PASSO 3 — Autentica Docker no Artifact Registry
# =============================================================
echo "🔑 Autenticando Docker no Artifact Registry..."
gcloud auth configure-docker $REGION-docker.pkg.dev --quiet

# =============================================================
# PASSO 4 — Gera requirements.txt
# =============================================================
echo "📋 Gerando requirements.txt..."
uv export --no-hashes --no-header --no-dev --no-emit-project --no-annotate > app/requirements.txt 2>/dev/null || \
uv export --no-hashes --no-header --no-dev --no-emit-project > app/requirements.txt

# =============================================================
# PASSO 5 — Build das imagens de produção
# =============================================================
echo "🔨 Buildando imagens..."
docker build -f Dockerfile.backend.prod -t $BACKEND_IMAGE .
docker build -f Dockerfile.frontend.prod -t $FRONTEND_IMAGE .

# =============================================================
# PASSO 6 — Push para o Artifact Registry
# =============================================================
echo "📤 Enviando imagens para o Artifact Registry..."
docker push $BACKEND_IMAGE
docker push $FRONTEND_IMAGE

# =============================================================
# PASSO 7 — Permissões da service account (só na primeira vez)
# =============================================================
echo "🔐 Configurando permissões..."
gcloud artifacts repositories add-iam-policy-binding $APP_NAME \
  --location=$REGION \
  --member="serviceAccount:$SERVICE_ACCOUNT" \
  --role="roles/artifactregistry.reader" \
  --project=$PROJECT_ID

gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member="serviceAccount:$SERVICE_ACCOUNT" \
  --role="roles/aiplatform.user"

gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member="serviceAccount:$SERVICE_ACCOUNT" \
  --role="roles/discoveryengine.editor"

# =============================================================
# PASSO 8 — Lê o .env removendo comentários e linhas vazias
# Garante que nenhum comentário inline corrompa os valores
# =============================================================
echo "📋 Lendo variáveis de ambiente..."
ENV_VARS=$(grep -v '^\s*#' app/.env | grep -v '^\s*$' | grep '=' | sed 's/#.*//' | sed 's/[[:space:]]*$//' | grep -v '=$' | tr '\n' ',' | sed 's/,$//')

echo "📋 Variáveis carregadas: $ENV_VARS"

# =============================================================
# PASSO 9 — Deploy do backend
# =============================================================
echo "🚀 Deployando backend..."
gcloud run deploy ${APP_NAME}-backend \
  --image=$BACKEND_IMAGE \
  --project=$PROJECT_ID \
  --region=$REGION \
  --service-account=$SERVICE_ACCOUNT \
  --set-env-vars="PYTHONUNBUFFERED=1,$ENV_VARS" \
  --allow-unauthenticated \
  --port=8000 \
  --memory=1Gi \
  --cpu=1 \
  --min-instances=0 \
  --max-instances=3

BACKEND_URL=$(gcloud run services describe ${APP_NAME}-backend \
  --project=$PROJECT_ID \
  --region=$REGION \
  --format="value(status.url)")

echo "✅ Backend deployado em: $BACKEND_URL"

# =============================================================
# PASSO 10 — Deploy do frontend
# BACKEND_URL é passado separadamente para evitar corrupção
# =============================================================
echo "🚀 Deployando frontend..."
gcloud run deploy ${APP_NAME}-frontend \
  --image=$FRONTEND_IMAGE \
  --project=$PROJECT_ID \
  --region=$REGION \
  --service-account=$SERVICE_ACCOUNT \
  --set-env-vars="NEXT_PUBLIC_API_URL=/api,BACKEND_URL=$BACKEND_URL,$ENV_VARS" \
  --allow-unauthenticated \
  --port=3000 \
  --memory=1Gi \
  --cpu=1 \
  --min-instances=0 \
  --max-instances=3

FRONTEND_URL=$(gcloud run services describe ${APP_NAME}-frontend \
  --project=$PROJECT_ID \
  --region=$REGION \
  --format="value(status.url)")

echo ""
echo "============================================"
echo "✅ Deploy concluído!"
echo "🌐 Acesse sua aplicação em: $FRONTEND_URL"
echo "🔧 Backend disponível em: $BACKEND_URL"
echo "============================================"