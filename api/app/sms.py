"""Envío de SMS por la API REST de Twilio.

Si Twilio no está configurado, no envía nada y devuelve el texto (modo simulado),
así la API funciona en local y en tests sin credenciales.
"""
import logging

import httpx

from .config import Config

log = logging.getLogger("aeroandes.sms")


def enviar_sms(cfg: Config, destino: str, texto: str) -> dict:
    to = cfg.demo_sms_to or destino
    if not cfg.twilio_configurado:
        log.info("SMS simulado a %s: %s", to, texto)
        return {"enviado": False, "modo": "simulado", "destino": to}

    url = f"https://api.twilio.com/2010-04-01/Accounts/{cfg.twilio_account_sid}/Messages.json"
    try:
        r = httpx.post(url, data={"From": cfg.twilio_from_number, "To": to, "Body": texto},
                       auth=(cfg.twilio_account_sid, cfg.twilio_auth_token), timeout=8.0)
        r.raise_for_status()
        return {"enviado": True, "modo": "twilio", "destino": to, "sid": r.json().get("sid")}
    except httpx.HTTPError as e:
        # Un SMS fallido no debe tumbar el cambio ya confirmado: se informa al agente.
        log.error("Fallo enviando SMS a %s: %s", to, e)
        return {"enviado": False, "modo": "error", "destino": to}
