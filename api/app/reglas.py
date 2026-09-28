"""Reglas de negocio de AeroAndes como funciones puras (sin I/O).

Reflejan kb/02-politica-cambios-reembolsos.md y kb/05-irregularidades-operacionales.md.
Mantenerlas aisladas permite probarlas sin base de datos ni red.
"""
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

CARGO_CAMBIO_CLASICA_USD = 50
HORAS_MINIMAS_ANTES_DE_SALIDA = 3
DIAS_VENTANA_REPROGRAMACION_CANCELACION = 7

ZONAS_AEROPUERTO = {
    "BOG": "America/Bogota",
    "MDE": "America/Bogota",
    "MEX": "America/Mexico_City",
    "EZE": "America/Argentina/Buenos_Aires",
    "SCL": "America/Santiago",
    "LIM": "America/Lima",
}


@dataclass(frozen=True)
class Elegibilidad:
    puede_cambiar: bool
    codigo: str
    explicacion: str
    sin_cargo: bool = False
    requiere_asesor: bool = False


@dataclass(frozen=True)
class Cotizacion:
    pasajeros: int
    cargo_por_pasajero: int
    diferencia_por_pasajero: int
    total_usd: int
    credito_usd: int
    detalle: str


def salida_local(vuelo: dict) -> datetime:
    zona = ZoneInfo(ZONAS_AEROPUERTO[vuelo["origen"]])
    h, m = (int(x) for x in vuelo["sale"].split(":"))
    return datetime.fromisoformat(vuelo["fecha"]).replace(hour=h, minute=m, tzinfo=zona)


def _dentro_de_plazo(vuelo: dict, ahora: datetime) -> bool:
    return salida_local(vuelo) - ahora >= timedelta(hours=HORAS_MINIMAS_ANTES_DE_SALIDA)


def evaluar_elegibilidad(reserva: dict, vuelo_actual: dict | None, ahora: datetime) -> Elegibilidad:
    estado = reserva["estado"]
    if estado == "VOLADA":
        return Elegibilidad(False, "VUELO_YA_REALIZADO", "Este vuelo ya se realizó; no se puede cambiar.")
    if estado == "CHECKIN_REALIZADO":
        return Elegibilidad(False, "CHECKIN_REALIZADO",
                            "El pasajero ya hizo check-in. El cambio lo hace un asesor humano o el mostrador del aeropuerto.",
                            requiere_asesor=True)
    cancelado = estado == "AFECTADA_CANCELACION" or (vuelo_actual or {}).get("estado") == "CANCELADO"
    if cancelado:
        return Elegibilidad(True, "CANCELACION_AEROLINEA",
                            "AeroAndes canceló el vuelo: la reprogramación no tiene ningún cargo, dentro de los 7 días siguientes.",
                            sin_cargo=True)
    if reserva["familia"] == "Basica":
        return Elegibilidad(False, "TARIFA_NO_PERMITE_CAMBIOS",
                            "La tarifa Básica no permite cambios de fecha ni de hora.")
    if vuelo_actual and not _dentro_de_plazo(vuelo_actual, ahora):
        return Elegibilidad(False, "FUERA_DE_PLAZO",
                            "Los cambios se hacen hasta 3 horas antes de la salida.", requiere_asesor=True)
    return Elegibilidad(True, "PERMITIDO", "El cambio está permitido según la tarifa.")


def validar_vuelo_nuevo(reserva: dict, vuelo_actual: dict, vuelo_nuevo: dict,
                        elegibilidad: Elegibilidad, ahora: datetime) -> str | None:
    """Devuelve un código de error, o None si el vuelo nuevo es válido."""
    if vuelo_nuevo["id"] == vuelo_actual["id"]:
        return "MISMO_VUELO"
    if (vuelo_nuevo["origen"], vuelo_nuevo["destino"]) != (vuelo_actual["origen"], vuelo_actual["destino"]):
        return "RUTA_DISTINTA"
    if vuelo_nuevo["estado"] != "PROGRAMADO":
        return "VUELO_NO_DISPONIBLE"
    if vuelo_nuevo["cupos"] < len(reserva["pasajeros"]):
        return "SIN_CUPO"
    if not _dentro_de_plazo(vuelo_nuevo, ahora):
        return "FUERA_DE_PLAZO"
    if elegibilidad.codigo == "CANCELACION_AEROLINEA":
        limite = date.fromisoformat(reserva["fecha"]) + timedelta(days=DIAS_VENTANA_REPROGRAMACION_CANCELACION)
        if date.fromisoformat(vuelo_nuevo["fecha"]) > limite:
            return "FUERA_DE_VENTANA_REPROGRAMACION"
    return None


def cotizar(reserva: dict, vuelo_nuevo: dict, elegibilidad: Elegibilidad) -> Cotizacion:
    n = len(reserva["pasajeros"])
    if elegibilidad.sin_cargo:
        return Cotizacion(n, 0, 0, 0, 0, "Sin cargo: vuelo cancelado por la aerolínea.")

    familia = reserva["familia"]
    pagado_por_pasajero = reserva["precio_pagado_usd"] / n
    tarifa_nueva = vuelo_nuevo["tarifas_usd"][familia]
    diferencia = round(tarifa_nueva - pagado_por_pasajero)
    cargo = 0 if familia == "Flex" else CARGO_CAMBIO_CLASICA_USD

    credito = 0
    if diferencia < 0:
        # Si el vuelo nuevo es más barato no se devuelve; en Flex queda como crédito.
        credito = -diferencia * n if familia == "Flex" else 0
        diferencia = 0

    total = n * (cargo + diferencia)
    partes = []
    if cargo:
        partes.append(f"cargo de cambio USD {cargo}")
    partes.append(f"diferencia de tarifa USD {diferencia}")
    detalle = " + ".join(partes) + (f", por {n} pasajeros" if n > 1 else "") + f" = USD {total}"
    if credito:
        detalle += f". Queda un crédito de USD {credito}."
    return Cotizacion(n, cargo, diferencia, total, credito, detalle)
