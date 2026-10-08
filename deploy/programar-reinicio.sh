#!/usr/bin/env bash
# Reinicia los datos de la demo cada hora con Cloud Scheduler, para que cada revisor que llame
# encuentre K7Q2MX en su estado original aunque otro revisor ya haya cambiado el vuelo.
# Correr una vez en Cloud Shell, desde la raíz del repo:  bash deploy/programar-reinicio.sh
# Para quitarlo después del proceso:
#   gcloud scheduler jobs delete aeroandes-reinicio --location us-east1
set -euo pipefail

PROJECT_ID="${PROJECT_ID:-ai-projects-510014}"
REGION="${REGION:-us-east1}"
SERVICE="${SERVICE:-aeroandes-api}"
JOB="${JOB:-aeroandes-reinicio}"
HORARIO="${HORARIO:-0 * * * *}"   # cada hora en punto

gcloud config set project "${PROJECT_ID}" >/dev/null
gcloud services enable cloudscheduler.googleapis.com >/dev/null

URL="$(gcloud run services describe "${SERVICE}" --region "${REGION}" --format='value(status.url)')"
SECRETO="$(gcloud secrets versions access latest --secret=agent-tools-secret)"

# El header queda guardado en la definición del job (visible solo para quien administre el
# proyecto). Es aceptable para una demo; en producción se usaría un token OIDC de una cuenta
# de servicio y Cloud Run con autenticación en esa ruta.
if gcloud scheduler jobs describe "${JOB}" --location "${REGION}" >/dev/null 2>&1; then
  ACCION=update; HEADERS_FLAG=--update-headers
else
  ACCION=create; HEADERS_FLAG=--headers
fi
gcloud scheduler jobs "${ACCION}" http "${JOB}" --location "${REGION}" \
  --schedule "${HORARIO}" --time-zone "America/Bogota" \
  --uri "${URL}/admin/reiniciar" --http-method POST \
  "${HEADERS_FLAG}" "X-Agent-Secret=${SECRETO}" \
  --attempt-deadline 60s >/dev/null

echo "==> Probando el job una vez"
gcloud scheduler jobs run "${JOB}" --location "${REGION}"
echo "Listo: ${JOB} reinicia los datos con el horario '${HORARIO}' (hora de Bogotá)."
