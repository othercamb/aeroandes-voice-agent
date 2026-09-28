"""Localización por país: se decide por el prefijo telefónico de quien llama.

Las voces son de la biblioteca de ElevenLabs y se validan escuchándolas por
teléfono antes de la grabación. Cambiarlas aquí no requiere tocar el agente.
"""
from dataclasses import dataclass


@dataclass(frozen=True)
class Pais:
    codigo: str
    nombre: str
    prefijo: str
    voice_id: str
    voz_nombre: str
    saludo: str
    trato: str  # indicación de registro para el LLM


PAISES = {
    "CO": Pais("CO", "Colombia", "+57", "1ZhMG5ZZgJ6XpkOrB8Az", "Luna",
               "¡Hola! Bienvenido a AeroAndes, habla Sofía, tu asistente virtual. ¿En qué te puedo ayudar hoy?",
               "Español de Colombia, cálido y cercano. Tutea con respeto; puede usar 'con gusto'."),
    "MX": Pais("MX", "México", "+52", "9Godp7dNohUvXk6qp0gS", "Regina",
               "¡Hola! Bienvenido a AeroAndes, te atiende Sofía, tu asistente virtual. ¿En qué te puedo ayudar?",
               "Español de México, amable. Puede usar 'claro que sí' y 'con mucho gusto'."),
    "AR": Pais("AR", "Argentina", "+54", "4wDRKlxcHNOFO5kBvE81", "Melisa",
               "¡Hola! Bienvenido a AeroAndes, te atiende Sofía, tu asistente virtual. ¿En qué te puedo ayudar?",
               "Español rioplatense: usa voseo ('vos tenés', 'contame'). Cordial y directo."),
    "CL": Pais("CL", "Chile", "+56", "6Gr4AVmTax1pMJO0lHRK", "Catalina",
               "¡Hola! Bienvenido a AeroAndes, te atiende Sofía, tu asistente virtual. ¿En qué te puedo ayudar?",
               "Español de Chile, cercano y profesional. Evita modismos muy coloquiales."),
    "PE": Pais("PE", "Perú", "+51", "ek0qR5Bu0N3aPdijsdae", "Lily",
               "¡Hola! Bienvenido a AeroAndes, te atiende Sofía, tu asistente virtual. ¿En qué te puedo ayudar?",
               "Español de Perú, amable y claro."),
}

PAIS_POR_DEFECTO = "CO"


def pais_por_telefono(telefono: str | None) -> Pais:
    """Devuelve el país según el prefijo. Si no se reconoce, usa Colombia (sede del BPO)."""
    if telefono:
        tel = telefono.strip().replace(" ", "")
        if not tel.startswith("+"):
            tel = "+" + tel
        # Prefijos de 3 caracteres (+5X): no hay ambigüedad entre los cinco países.
        for pais in PAISES.values():
            if tel.startswith(pais.prefijo):
                return pais
    return PAISES[PAIS_POR_DEFECTO]
