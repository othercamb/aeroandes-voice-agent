"""Genera los datos ficticios de AeroAndes para la demo del take-home.

Salida:
  vuelos.json   -> inventario de vuelos con fecha, cupos y tarifa por familia
  reservas.json -> 12 reservas de prueba (golden path + casos fuera del guion)

Todo es ficticio. Ejecutar: python3 generar_datos.py
"""
import json
import hashlib
from datetime import date, timedelta
from pathlib import Path

AQUI = Path(__file__).parent

# Itinerario base de AeroAndes (hub Bogotá). Horas locales de salida.
ITINERARIO = [
    # vuelo, origen, destino, sale, llega, precio base Clásica USD
    ("AN101", "BOG", "MEX", "07:10", "11:05", 289),
    ("AN103", "BOG", "MEX", "15:40", "19:35", 269),
    ("AN102", "MEX", "BOG", "13:15", "18:50", 289),
    ("AN201", "BOG", "EZE", "09:05", "17:30", 419),
    ("AN202", "EZE", "BOG", "17:00", "22:10", 419),
    ("AN301", "BOG", "SCL", "08:20", "15:45", 389),
    ("AN302", "SCL", "BOG", "16:10", "21:05", 389),
    ("AN401", "BOG", "LIM", "06:45", "09:55", 219),
    ("AN403", "BOG", "LIM", "18:30", "21:40", 199),
    ("AN402", "LIM", "BOG", "11:30", "14:50", 219),
    ("AN501", "BOG", "MDE", "12:00", "13:00", 79),
]

# Multiplicadores por familia tarifaria (ver kb/politica-cambios-reembolsos.md)
FAMILIAS = {"Basica": 0.75, "Clasica": 1.00, "Flex": 1.45}

INICIO, FIN = date(2026, 10, 15), date(2026, 11, 5)

# Ajustes explícitos para que la demo sea predecible.
AJUSTES = {
    # Golden path: Valentina pasa del 20 al 22 de octubre en AN101.
    ("AN101", "2026-10-20"): {"cupos": 12, "precio_clasica": 289},
    ("AN101", "2026-10-21"): {"cupos": 0, "precio_clasica": 289},   # lleno: fuerza alternativa
    ("AN101", "2026-10-22"): {"cupos": 9, "precio_clasica": 319},   # diferencia USD 30
    ("AN103", "2026-10-22"): {"cupos": 4, "precio_clasica": 299},   # alternativa de la tarde
    # Vuelo cancelado por la aerolínea (caso irregularidad operacional).
    ("AN103", "2026-10-16"): {"estado": "CANCELADO", "motivo": "condiciones meteorologicas en destino"},
}


def _determinista(clave: str, minimo: int, maximo: int) -> int:
    h = int(hashlib.sha256(clave.encode()).hexdigest(), 16)
    return minimo + h % (maximo - minimo + 1)


def generar_vuelos():
    vuelos = []
    d = INICIO
    while d <= FIN:
        for num, org, dst, sale, llega, base in ITINERARIO:
            f = d.isoformat()
            clave = f"{num}-{f}"
            variacion = _determinista(clave, -20, 40)  # precio varía por fecha
            clasica = base + variacion
            registro = {
                "id": clave,
                "vuelo": num,
                "origen": org,
                "destino": dst,
                "fecha": f,
                "sale": sale,
                "llega": llega,
                "estado": "PROGRAMADO",
                "cupos": _determinista(clave + "c", 0, 40),
                "tarifas_usd": {},
            }
            aj = AJUSTES.get((num, f), {})
            if "precio_clasica" in aj:
                clasica = aj["precio_clasica"]
            for fam, mult in FAMILIAS.items():
                registro["tarifas_usd"][fam] = round(clasica * mult)
            registro["tarifas_usd"]["Clasica"] = clasica
            for k in ("cupos", "estado", "motivo"):
                if k in aj:
                    registro[k] = aj[k]
            if registro["estado"] == "CANCELADO":
                registro["cupos"] = 0
            vuelos.append(registro)
        d += timedelta(days=1)
    return vuelos


RESERVAS = [
    # --- Golden path -------------------------------------------------------
    {
        "pnr": "K7Q2MX", "pais": "CO", "telefono": "+573104567890",
        "pasajeros": [{"nombre": "Valentina", "apellido": "Rojas"}],
        "vuelo": "AN101", "fecha": "2026-10-20", "familia": "Clasica",
        "precio_pagado_usd": 289, "equipaje_bodega": 1, "estado": "CONFIRMADA",
        "nota_demo": "Golden path: cambio al 22-oct. El 21 está lleno. Opciones: AN101 mañana (cargo 50 + diferencia 30 = USD 80) o AN103 tarde (50 + 10 = USD 60).",
    },
    # --- Colombia ----------------------------------------------------------
    {
        "pnr": "H3LM9P", "pais": "CO", "telefono": "+573157771122",
        "pasajeros": [{"nombre": "Andres", "apellido": "Gomez"}],
        "vuelo": "AN501", "fecha": "2026-10-18", "familia": "Basica",
        "precio_pagado_usd": 61, "equipaje_bodega": 0, "estado": "CONFIRMADA",
        "nota_demo": "Tarifa Básica: no admite cambios. El agente explica y ofrece opciones sin inventar excepciones.",
    },
    {
        "pnr": "R8TZ4C", "pais": "CO", "telefono": "+573006543210",
        "pasajeros": [{"nombre": "Mariana", "apellido": "Ospina"}],
        "vuelo": "AN401", "fecha": "2026-10-24", "familia": "Flex",
        "precio_pagado_usd": 318, "equipaje_bodega": 2, "estado": "CONFIRMADA",
        "nota_demo": "Pregunta por viajar con su gato en cabina (base de conocimiento: mascotas).",
    },
    {
        "pnr": "C3YT7Q", "pais": "CO", "telefono": "+573209988776",
        "pasajeros": [{"nombre": "Sofia", "apellido": "Ramirez"},
                      {"nombre": "Tomas", "apellido": "Ramirez"}],
        "vuelo": "AN201", "fecha": "2026-10-30", "familia": "Clasica",
        "precio_pagado_usd": 838, "equipaje_bodega": 2, "estado": "CONFIRMADA",
        "nota_demo": "Dos pasajeros: el cambio aplica cargo por pasajero.",
    },
    # --- México ------------------------------------------------------------
    {
        "pnr": "M2XP6D", "pais": "MX", "telefono": "+525512345678",
        "pasajeros": [{"nombre": "Jose Luis", "apellido": "Hernandez"}],
        "vuelo": "AN102", "fecha": "2026-10-21", "familia": "Clasica",
        "precio_pagado_usd": 289, "equipaje_bodega": 1, "estado": "CONFIRMADA",
        "nota_demo": "Pasajero de México: saludo y voz con acento mexicano.",
    },
    {
        "pnr": "F9CN3E", "pais": "MX", "telefono": "+523398765432",
        "pasajeros": [{"nombre": "Daniela", "apellido": "Martinez"}],
        "vuelo": "AN103", "fecha": "2026-10-16", "familia": "Basica",
        "precio_pagado_usd": 202, "equipaje_bodega": 0, "estado": "AFECTADA_CANCELACION",
        "nota_demo": "Vuelo cancelado por la aerolínea: reprogramación sin costo aunque sea Básica.",
    },
    # --- Argentina ---------------------------------------------------------
    {
        "pnr": "B4VW7G", "pais": "AR", "telefono": "+5491145678901",
        "pasajeros": [{"nombre": "Lucia", "apellido": "Fernandez"}],
        "vuelo": "AN202", "fecha": "2026-10-25", "familia": "Flex",
        "precio_pagado_usd": 608, "equipaje_bodega": 2, "estado": "CONFIRMADA",
        "nota_demo": "Flex: cambio sin cargo, solo diferencia tarifaria. Pide reembolso: aplica.",
    },
    {
        "pnr": "T6JR2H", "pais": "AR", "telefono": "+5493514567890",
        "pasajeros": [{"nombre": "Martin", "apellido": "Pereyra"}],
        "vuelo": "AN201", "fecha": "2026-10-19", "familia": "Basica",
        "precio_pagado_usd": 314, "equipaje_bodega": 0, "estado": "CONFIRMADA",
        "nota_demo": "Quiere agregar una maleta de bodega (costo adicional según política).",
    },
    # --- Chile -------------------------------------------------------------
    {
        "pnr": "P5SK8J", "pais": "CL", "telefono": "+56987654321",
        "pasajeros": [{"nombre": "Camila", "apellido": "Soto"}],
        "vuelo": "AN301", "fecha": "2026-10-05", "familia": "Clasica",
        "precio_pagado_usd": 389, "equipaje_bodega": 1, "estado": "VOLADA",
        "reclamo_equipaje": {"referencia": "SCLAN00482", "estado": "EN_BUSQUEDA",
                             "ultima_actualizacion": "2026-10-07",
                             "detalle": "Maleta ubicada en BOG, en tránsito a SCL"},
        "nota_demo": "Consulta el estado de su maleta demorada.",
    },
    {
        "pnr": "N1DH5L", "pais": "CL", "telefono": "+56912345678",
        "pasajeros": [{"nombre": "Ignacio", "apellido": "Vargas"}],
        "vuelo": "AN301", "fecha": "2026-10-28", "familia": "Flex",
        "precio_pagado_usd": 564, "equipaje_bodega": 2, "estado": "CONFIRMADA",
        "nota_demo": "Cambia de opinión a mitad del proceso (caso fuera del guion).",
    },
    # --- Perú --------------------------------------------------------------
    {
        "pnr": "G8FQ3M", "pais": "PE", "telefono": "+51987654321",
        "pasajeros": [{"nombre": "Rosa", "apellido": "Quispe"}],
        "vuelo": "AN402", "fecha": "2026-10-22", "familia": "Clasica",
        "precio_pagado_usd": 219, "equipaje_bodega": 1, "estado": "CONFIRMADA",
        "nota_demo": "Pasajera de Perú: saludo y voz con acento peruano.",
    },
    {
        "pnr": "W2LB9N", "pais": "PE", "telefono": "+51912345678",
        "pasajeros": [{"nombre": "Diego", "apellido": "Salazar"}],
        "vuelo": "AN403", "fecha": "2026-10-17", "familia": "Clasica",
        "precio_pagado_usd": 199, "equipaje_bodega": 1, "estado": "CHECKIN_REALIZADO",
        "nota_demo": "Ya hizo check-in: el cambio no se puede por teléfono, se transfiere a un asesor.",
    },
]


def main():
    vuelos = generar_vuelos()
    (AQUI / "vuelos.json").write_text(json.dumps(vuelos, ensure_ascii=False, indent=2))
    (AQUI / "reservas.json").write_text(json.dumps(RESERVAS, ensure_ascii=False, indent=2))
    print(f"{len(vuelos)} vuelos, {len(RESERVAS)} reservas")


if __name__ == "__main__":
    main()
