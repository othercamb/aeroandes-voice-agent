"""Configuración leída de variables de entorno.

En Cloud Run los secretos llegan como variables inyectadas desde Secret Manager.
"""
import os
from dataclasses import dataclass, field
from pathlib import Path

RAIZ_REPO = Path(__file__).resolve().parents[2]


@dataclass(frozen=True)
class Config:
    # "memoria" para desarrollo y tests; "firestore" en Cloud Run.
    almacenamiento: str = field(default_factory=lambda: os.getenv("STORAGE", "memoria"))
    gcp_project_id: str = field(default_factory=lambda: os.getenv("GCP_PROJECT_ID", ""))
    firestore_db: str = field(default_factory=lambda: os.getenv("FIRESTORE_DB", "(default)"))

    # Secreto compartido: ElevenLabs lo envía en el header X-Agent-Secret.
    agent_tools_secret: str = field(default_factory=lambda: os.getenv("AGENT_TOOLS_SECRET", ""))

    twilio_account_sid: str = field(default_factory=lambda: os.getenv("TWILIO_ACCOUNT_SID", ""))
    twilio_auth_token: str = field(default_factory=lambda: os.getenv("TWILIO_AUTH_TOKEN", ""))
    twilio_from_number: str = field(default_factory=lambda: os.getenv("TWILIO_FROM_NUMBER", ""))

    # En la demo las reservas tienen teléfonos ficticios. Si se define, TODOS los SMS
    # van a este número (el celular de quien presenta). Nunca se escribe a números inventados.
    demo_sms_to: str = field(default_factory=lambda: os.getenv("DEMO_SMS_TO", ""))

    # URL pública de la API, para armar el enlace de pago del SMS.
    url_publica: str = field(default_factory=lambda: os.getenv("PUBLIC_BASE_URL", "http://localhost:8080"))

    # "Hoy" fijo del mundo de la demo (ISO 8601 con zona). Los vuelos son de octubre de 2026;
    # congelar la fecha permite que el golden path funcione igual cuando los FDE lo prueben
    # días después de la entrega. Vacío = hora real.
    demo_now: str = field(default_factory=lambda: os.getenv("DEMO_NOW", ""))

    dir_datos: Path = field(default_factory=lambda: Path(os.getenv("DATA_DIR", RAIZ_REPO / "data")))

    @property
    def twilio_configurado(self) -> bool:
        return bool(self.twilio_account_sid and self.twilio_auth_token and self.twilio_from_number)
