#!/usr/bin/env bash
# Despliega la API de AeroAndes en Cloud Run. Pensado para correr en Cloud Shell
# desde la raíz del repo:  bash deploy/deploy.sh
#
# Es idempotente: se puede volver a correr para redesplegar.
# Variables opcionales (exportarlas antes de correr):
#   TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN, TWILIO_FROM_NUMBER  → habilita SMS reales
#   DEMO_SMS_TO   → número que recibe TODOS los SMS de la demo (tu celular, formato +57...)
set -euo pipefail

PROJECT_ID="${PROJECT_ID:-ai-projects-510014}"
REGION="${REGION:-us-east1}"
SERVICE="${SERVICE:-aeroandes-api}"
FIRESTORE_DB="${FIRESTORE_DB:-aeroandes}"          # base con nombre propio: no toca la (default)
SA_NAME="${SA_NAME:-aeroandes-api}"
SA="${SA_NAME}@${PROJECT_ID}.iam.gserviceaccount.com"
DEMO_NOW="${DEMO_NOW:-2026-10-13T10:00:00-05:00}" # "hoy" fijo del mundo de la demo

echo "==> Proyecto ${PROJECT_ID}, región ${REGION}"
gcloud config set project "${PROJECT_ID}" >/dev/null

echo "==> Habilitando APIs"
gcloud services enable run.googleapis.com cloudbuild.googleapis.com artifactregistry.googleapis.com \
  firestore.googleapis.com secretmanager.googleapis.com >/dev/null

echo "==> Firestore (${FIRESTORE_DB})"
if ! gcloud firestore databases describe --database="${FIRESTORE_DB}" >/dev/null 2>&1; then
  gcloud firestore databases create --database="${FIRESTORE_DB}" --location="${REGION}" --type=firestore-native
fi

echo "==> Cuenta de servicio con permisos mínimos"
if ! gcloud iam service-accounts describe "${SA}" >/dev/null 2>&1; then
  gcloud iam service-accounts create "${SA_NAME}" --display-name="AeroAndes API"
fi
gcloud projects add-iam-policy-binding "${PROJECT_ID}" --member="serviceAccount:${SA}" \
  --role="roles/datastore.user" --condition=None >/dev/null

# Crea o actualiza un secreto y le da acceso solo a la cuenta de servicio.
guardar_secreto() {
  local nombre="$1" valor="$2"
  if ! gcloud secrets describe "${nombre}" >/dev/null 2>&1; then
    gcloud secrets create "${nombre}" --replication-policy=automatic >/dev/null
  fi
  printf '%s' "${valor}" | gcloud secrets versions add "${nombre}" --data-file=- >/dev/null
  gcloud secrets add-iam-policy-binding "${nombre}" --member="serviceAccount:${SA}" \
    --role="roles/secretmanager.secretAccessor" >/dev/null
}

echo "==> Secretos"
if ! gcloud secrets describe agent-tools-secret >/dev/null 2>&1; then
  guardar_secreto agent-tools-secret "$(openssl rand -hex 24)"
  echo "    agent-tools-secret creado"
fi
SECRETS="AGENT_TOOLS_SECRET=agent-tools-secret:latest"
if [[ -n "${TWILIO_ACCOUNT_SID:-}" && -n "${TWILIO_AUTH_TOKEN:-}" ]]; then
  guardar_secreto twilio-account-sid "${TWILIO_ACCOUNT_SID}"
  guardar_secreto twilio-auth-token "${TWILIO_AUTH_TOKEN}"
  echo "    secretos de Twilio actualizados"
fi
if gcloud secrets describe twilio-auth-token >/dev/null 2>&1; then
  SECRETS="${SECRETS},TWILIO_ACCOUNT_SID=twilio-account-sid:latest,TWILIO_AUTH_TOKEN=twilio-auth-token:latest"
fi

ENV_VARS="STORAGE=firestore,GCP_PROJECT_ID=${PROJECT_ID},FIRESTORE_DB=${FIRESTORE_DB},DEMO_NOW=${DEMO_NOW}"
[[ -n "${TWILIO_FROM_NUMBER:-}" ]] && ENV_VARS="${ENV_VARS},TWILIO_FROM_NUMBER=${TWILIO_FROM_NUMBER}"
[[ -n "${DEMO_SMS_TO:-}" ]] && ENV_VARS="${ENV_VARS},DEMO_SMS_TO=${DEMO_SMS_TO}"

echo "==> Construyendo y desplegando en Cloud Run"
# --allow-unauthenticated: ElevenLabs llama desde internet; la protección es el header X-Agent-Secret.
# --min-instances 1: sin arranque en frío en mitad de una llamada de voz.
gcloud run deploy "${SERVICE}" --source . --region "${REGION}" \
  --service-account "${SA}" --allow-unauthenticated \
  --min-instances 1 --max-instances 3 --cpu 1 --memory 512Mi --concurrency 40 \
  --set-env-vars "${ENV_VARS}" --update-secrets "${SECRETS}"

URL="$(gcloud run services describe "${SERVICE}" --region "${REGION}" --format='value(status.url)')"
gcloud run services update "${SERVICE}" --region "${REGION}" \
  --update-env-vars "PUBLIC_BASE_URL=${URL}" >/dev/null

echo "==> Sembrando datos de la demo"
SECRETO="$(gcloud secrets versions access latest --secret=agent-tools-secret)"
curl -fsS -X POST "${URL}/admin/reiniciar" -H "X-Agent-Secret: ${SECRETO}" && echo

echo "==> Prueba de salud"
curl -fsS "${URL}/salud" && echo
echo
echo "Listo. URL de la API: ${URL}"
echo "El secreto para configurar las herramientas en ElevenLabs está en Secret Manager (agent-tools-secret)."
