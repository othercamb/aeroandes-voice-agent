# Imagen de la API para Cloud Run. Se construye desde la raíz del repo
# porque la API necesita data/ para sembrar y reiniciar la demo.
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PORT=8080 DATA_DIR=/srv/data
WORKDIR /srv

COPY api/requirements.txt api/requirements.txt
RUN pip install --no-cache-dir -r api/requirements.txt

COPY api/app api/app
COPY data data

WORKDIR /srv/api
# Un solo worker: el estado vive en Firestore y Cloud Run escala por instancias.
CMD exec uvicorn app.main:app --host 0.0.0.0 --port ${PORT} --workers 1
