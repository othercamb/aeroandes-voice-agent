"""API de AeroAndes para el agente de voz de ElevenLabs.

Rutas:
  POST /webhooks/inicio-conversacion   webhook de inicio: país → voz, saludo y variables
  POST /herramientas/consultar-reserva  verificación (código + apellido) y resumen
  POST /herramientas/buscar-vuelos      alternativas con cotización según la política
  POST /herramientas/cambiar-vuelo      ejecuta el cambio y envía el SMS con enlace de pago
  POST /herramientas/estado-equipaje    estado de un reclamo de maleta
  GET/POST /pagar/{token}               página de pago simulado (el enlace del SMS)
  POST /admin/reiniciar                 vuelve los datos al estado inicial entre ensayos
  GET  /salud
"""
import hmac
import html
import logging
import secrets
import unicodedata
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

from fastapi import Depends, FastAPI, Header, HTTPException
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field

from . import reglas
from .config import Config
from .paises import PAISES, pais_por_telefono
from .repositorio import (Repositorio, RepositorioFirestore, RepositorioMemoria,
                          SinCupoError, cargar_semilla)
from .sms import enviar_sms

logging.basicConfig(level=logging.INFO)
log = logging.getLogger("aeroandes.api")

BOGOTA = ZoneInfo("America/Bogota")
CIUDADES = {"BOG": "Bogotá", "MDE": "Medellín", "MEX": "Ciudad de México",
            "EZE": "Buenos Aires", "SCL": "Santiago", "LIM": "Lima"}
FAMILIA_LEGIBLE = {"Basica": "Básica", "Clasica": "Clásica", "Flex": "Flex"}


# ---------- Modelos de entrada (lo que envía el agente) ----------------------

class Verificacion(BaseModel):
    codigo_reserva: str = Field(description="Código de 6 caracteres, por ejemplo K7Q2MX")
    apellido: str = Field(description="Apellido de uno de los pasajeros")


class BuscarVuelos(Verificacion):
    fecha_deseada: date = Field(description="Fecha a la que quiere cambiar, formato AAAA-MM-DD")


class CambiarVuelo(Verificacion):
    vuelo_id: str = Field(description="id del vuelo elegido, tal como lo devolvió buscar-vuelos")
    confirmacion_cliente: bool = Field(description="true solo si el cliente dijo explícitamente que confirma")


class EstadoEquipaje(BaseModel):
    referencia: str = Field(description="Referencia de 10 caracteres del reclamo, por ejemplo SCLAN00482")
    apellido: str


class InicioConversacion(BaseModel):
    caller_id: str | None = None
    called_number: str | None = None
    agent_id: str | None = None
    call_sid: str | None = None
    pais: str | None = Field(default=None, description="Solo para pruebas: fuerza el país (CO, MX, AR, CL, PE)")


# ---------- Utilidades ----------------------------------------------------------

def _normalizar(texto: str) -> str:
    sin_tildes = unicodedata.normalize("NFKD", texto).encode("ascii", "ignore").decode()
    return " ".join(sin_tildes.casefold().split())


def _codigo(texto: str) -> str:
    return "".join(texto.split()).upper()


def _describir_vuelo(v: dict) -> dict:
    return {
        "vuelo_id": v["id"],
        "numero": v["vuelo"],
        "ruta": f'{CIUDADES[v["origen"]]} a {CIUDADES[v["destino"]]}',
        "fecha": v["fecha"],
        "hora_salida": v["sale"],
        "hora_llegada": v["llega"],
        "estado": v["estado"],
    }


def crear_app(cfg: Config | None = None, repo: Repositorio | None = None, reloj=None) -> FastAPI:
    cfg = cfg or Config()
    if repo is None:
        if cfg.almacenamiento == "firestore":
            repo = RepositorioFirestore(cfg.gcp_project_id, cfg.firestore_db)
        else:
            repo = RepositorioMemoria(*cargar_semilla(cfg.dir_datos))

    def ahora() -> datetime:
        if reloj:
            return reloj()
        if cfg.demo_now:
            return datetime.fromisoformat(cfg.demo_now)
        return datetime.now(BOGOTA)

    app = FastAPI(title="AeroAndes API", version="1.0.0")

    def autenticar(x_agent_secret: str | None = Header(default=None)):
        if not cfg.agent_tools_secret:
            if cfg.almacenamiento == "memoria":
                return  # desarrollo local sin secreto
            raise HTTPException(503, "Secreto de herramientas no configurado")
        if not x_agent_secret or not hmac.compare_digest(x_agent_secret, cfg.agent_tools_secret):
            raise HTTPException(401, "No autorizado")

    def verificar(codigo: str, apellido: str) -> dict | None:
        reserva = repo.obtener_reserva(_codigo(codigo))
        if not reserva:
            return None
        if _normalizar(apellido) not in {_normalizar(p["apellido"]) for p in reserva["pasajeros"]}:
            return None
        return reserva

    NO_VERIFICADO = {
        "verificado": False,
        "mensaje": "El código de reserva y el apellido no coinciden.",
        "indicacion": "Pide los datos una vez más. Si vuelven a fallar, ofrece un asesor humano. "
                      "No confirmes ni niegues que la reserva exista.",
    }

    # ---------- Salud y webhook de inicio ----------------------------------------

    @app.get("/salud")
    def salud():
        return {"ok": True, "almacenamiento": cfg.almacenamiento, "ahora": ahora().isoformat()}

    @app.post("/webhooks/inicio-conversacion", dependencies=[Depends(autenticar)])
    def inicio_conversacion(datos: InicioConversacion):
        pais = PAISES.get((datos.pais or "").upper()) or pais_por_telefono(datos.caller_id)
        log.info("Inicio de conversación: caller=%s → país %s", datos.caller_id, pais.codigo)
        return {
            "type": "conversation_initiation_client_data",
            "dynamic_variables": {
                "pais": pais.nombre,
                "pais_codigo": pais.codigo,
                "trato_regional": pais.trato,
                "telefono_cliente": datos.caller_id or "",
            },
            "conversation_config_override": {
                "agent": {"first_message": pais.saludo, "language": "es"},
                "tts": {"voice_id": pais.voice_id},
            },
        }

    # ---------- Herramientas -------------------------------------------------------

    @app.post("/herramientas/consultar-reserva", dependencies=[Depends(autenticar)])
    def consultar_reserva(datos: Verificacion):
        reserva = verificar(datos.codigo_reserva, datos.apellido)
        if not reserva:
            return NO_VERIFICADO
        vuelo = repo.obtener_vuelo(f'{reserva["vuelo"]}-{reserva["fecha"]}')
        eleg = reglas.evaluar_elegibilidad(reserva, vuelo, ahora())
        resp = {
            "verificado": True,
            "codigo_reserva": reserva["pnr"],
            "pasajeros": [f'{p["nombre"]} {p["apellido"]}' for p in reserva["pasajeros"]],
            "tarifa": FAMILIA_LEGIBLE[reserva["familia"]],
            "estado_reserva": reserva["estado"],
            "maletas_bodega_incluidas": reserva["equipaje_bodega"],
            "vuelo": _describir_vuelo(vuelo) if vuelo else {
                "numero": reserva["vuelo"], "fecha": reserva["fecha"], "estado": "REALIZADO"},
            "cambio": {
                "permitido": eleg.puede_cambiar,
                "codigo": eleg.codigo,
                "explicacion": eleg.explicacion,
                "sin_cargo": eleg.sin_cargo,
                "requiere_asesor": eleg.requiere_asesor,
            },
        }
        if vuelo and vuelo["estado"] == "CANCELADO":
            resp["vuelo"]["motivo_cancelacion"] = vuelo.get("motivo")
        return resp

    @app.post("/herramientas/buscar-vuelos", dependencies=[Depends(autenticar)])
    def buscar_vuelos(datos: BuscarVuelos):
        reserva = verificar(datos.codigo_reserva, datos.apellido)
        if not reserva:
            return NO_VERIFICADO
        actual = repo.obtener_vuelo(f'{reserva["vuelo"]}-{reserva["fecha"]}')
        t = ahora()
        eleg = reglas.evaluar_elegibilidad(reserva, actual, t)
        if not eleg.puede_cambiar or not actual:
            return {"verificado": True, "permitido": False, "codigo": eleg.codigo,
                    "explicacion": eleg.explicacion, "requiere_asesor": eleg.requiere_asesor}

        def opciones_en(desde: date, hasta: date):
            candidatos = repo.vuelos_ruta(actual["origen"], actual["destino"],
                                          desde.isoformat(), hasta.isoformat())
            validas, llenos = [], []
            for v in candidatos:
                error = reglas.validar_vuelo_nuevo(reserva, actual, v, eleg, t)
                if error is None:
                    c = reglas.cotizar(reserva, v, eleg)
                    validas.append({**_describir_vuelo(v), "cupos_disponibles": v["cupos"],
                                    "total_a_pagar_usd": c.total_usd, "detalle_cobro": c.detalle})
                elif error == "SIN_CUPO" and v["fecha"] == datos.fecha_deseada.isoformat():
                    llenos.append(v["vuelo"])
            return validas, llenos

        d = datos.fecha_deseada
        opciones, llenos = opciones_en(d, d)
        alternativas_cercanas = False
        if not opciones:
            opciones, _ = opciones_en(d - timedelta(days=2), d + timedelta(days=2))
            alternativas_cercanas = True
        return {
            "verificado": True,
            "permitido": True,
            "fecha_pedida": d.isoformat(),
            "vuelos_llenos_en_fecha_pedida": llenos,
            "son_alternativas_cercanas": alternativas_cercanas,
            "opciones": opciones[:4],
            "indicacion": "Lee máximo dos o tres opciones con hora y total. No ejecutes el cambio "
                          "hasta que el cliente elija y confirme explícitamente.",
        }

    @app.post("/herramientas/cambiar-vuelo", dependencies=[Depends(autenticar)])
    def cambiar_vuelo(datos: CambiarVuelo):
        reserva = verificar(datos.codigo_reserva, datos.apellido)
        if not reserva:
            return NO_VERIFICADO
        if not datos.confirmacion_cliente:
            return {"ejecutado": False, "codigo": "FALTA_CONFIRMACION",
                    "indicacion": "Lee el vuelo nuevo y el total, y pide confirmación explícita antes de ejecutar."}
        actual = repo.obtener_vuelo(f'{reserva["vuelo"]}-{reserva["fecha"]}')
        nuevo = repo.obtener_vuelo(datos.vuelo_id.strip())
        if not actual or not nuevo:
            return {"ejecutado": False, "codigo": "VUELO_NO_ENCONTRADO",
                    "indicacion": "Usa un vuelo_id devuelto por buscar-vuelos."}
        t = ahora()
        eleg = reglas.evaluar_elegibilidad(reserva, actual, t)
        if not eleg.puede_cambiar:
            return {"ejecutado": False, "codigo": eleg.codigo, "explicacion": eleg.explicacion,
                    "requiere_asesor": eleg.requiere_asesor}
        error = reglas.validar_vuelo_nuevo(reserva, actual, nuevo, eleg, t)
        if error:
            return {"ejecutado": False, "codigo": error,
                    "indicacion": "Vuelve a buscar vuelos y ofrece otra opción."}

        cot = reglas.cotizar(reserva, nuevo, eleg)
        evento = {"tipo": "CAMBIO", "de": actual["id"], "a": nuevo["id"], "total_usd": cot.total_usd,
                  "motivo": eleg.codigo, "fecha": t.isoformat()}
        try:
            reserva = repo.aplicar_cambio(reserva["pnr"], nuevo["id"], evento)
        except SinCupoError:
            return {"ejecutado": False, "codigo": "SIN_CUPO",
                    "indicacion": "El vuelo se llenó en este momento. Ofrece otra opción."}

        destino_sms = reserva["telefono"]
        fecha_txt = datetime.fromisoformat(nuevo["fecha"]).strftime("%d/%m")
        if cot.total_usd > 0:
            token = secrets.token_urlsafe(9)
            repo.guardar_pago(token, {"pnr": reserva["pnr"], "total_usd": cot.total_usd,
                                      "detalle": cot.detalle, "vuelo": nuevo["vuelo"],
                                      "fecha": nuevo["fecha"], "sale": nuevo["sale"],
                                      "estado": "PENDIENTE", "creado": t.isoformat()})
            enlace = f"{cfg.url_publica.rstrip('/')}/pagar/{token}"
            texto = (f"AeroAndes: tu reserva {reserva['pnr']} quedó en el vuelo {nuevo['vuelo']} "
                     f"del {fecha_txt} a las {nuevo['sale']}. Total USD {cot.total_usd}. "
                     f"Paga aquí: {enlace} (vence en 2 horas).")
        else:
            enlace = None
            texto = (f"AeroAndes: tu reserva {reserva['pnr']} quedó en el vuelo {nuevo['vuelo']} "
                     f"del {fecha_txt} a las {nuevo['sale']}. Sin costo. ¡Buen viaje!")
        sms = enviar_sms(cfg, destino_sms, texto)
        if sms["modo"] == "error":
            indicacion = "El cambio quedó hecho, pero el SMS falló: dile que un asesor le enviará el enlace."
        elif enlace:
            indicacion = "Confirma el cambio y avisa que le llegó un SMS con el enlace de pago, que vence en 2 horas."
        else:
            indicacion = "Confirma el cambio sin costo y avisa que le llegó un SMS de confirmación."

        return {
            "ejecutado": True,
            "codigo_reserva": reserva["pnr"],
            "vuelo_nuevo": _describir_vuelo(nuevo),
            "total_a_pagar_usd": cot.total_usd,
            "detalle_cobro": cot.detalle,
            "credito_usd": cot.credito_usd,
            "sms_enviado": sms["enviado"],
            "enlace_pago_enviado": enlace is not None,
            "indicacion": indicacion,
        }

    @app.post("/herramientas/estado-equipaje", dependencies=[Depends(autenticar)])
    def estado_equipaje(datos: EstadoEquipaje):
        reclamo = repo.obtener_reclamo(_codigo(datos.referencia))
        if not reclamo:
            return {"encontrado": False, "indicacion": "Pide la referencia de nuevo, letra por letra."}
        reserva = repo.obtener_reserva(reclamo["pnr"])
        if not reserva or _normalizar(datos.apellido) not in {_normalizar(p["apellido"]) for p in reserva["pasajeros"]}:
            return {"encontrado": False, "indicacion": "Los datos no coinciden. No des información del reclamo."}
        dias = (ahora().date() - date.fromisoformat(reclamo["ultima_actualizacion"])).days
        return {
            "encontrado": True,
            "referencia": reclamo["referencia"],
            "estado": reclamo["estado"],
            "detalle": reclamo["detalle"],
            "ultima_actualizacion": reclamo["ultima_actualizacion"],
            "dias_desde_actualizacion": dias,
            "gastos_reconocidos": "Hasta USD 50 por día, máximo 5 días, con recibos.",
        }

    # ---------- Página de pago simulado --------------------------------------------

    def _pagina(titulo: str, cuerpo: str) -> HTMLResponse:
        return HTMLResponse(f"""<!doctype html><html lang="es"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><title>{titulo}</title>
<style>body{{font-family:system-ui,sans-serif;background:#f4f6fb;margin:0;padding:24px;color:#1b2333}}
.card{{max-width:420px;margin:auto;background:#fff;border-radius:14px;padding:24px;box-shadow:0 4px 18px #0001}}
h1{{font-size:20px;margin:0 0 4px}} .muted{{color:#5b6475;font-size:14px}}
.total{{font-size:32px;font-weight:700;margin:16px 0}} button{{width:100%;padding:14px;border:0;border-radius:10px;
background:#1f5eff;color:#fff;font-size:16px;font-weight:600}} .ok{{color:#138a4c;font-weight:700}}</style></head>
<body><div class="card"><p class="muted">AeroAndes · pago seguro (simulado para la demo)</p>{cuerpo}</div></body></html>""")

    @app.get("/pagar/{token}", response_class=HTMLResponse)
    def ver_pago(token: str):
        pago = repo.obtener_pago(token)
        if not pago:
            return _pagina("Enlace no válido", "<h1>Enlace no válido</h1><p class='muted'>El enlace no existe o venció.</p>")
        if pago["estado"] == "PAGADO":
            return _pagina("Pago recibido", f"<h1 class='ok'>Pago recibido</h1><p>Reserva {html.escape(pago['pnr'])}</p>")
        return _pagina("Pagar cambio", f"""<h1>Cambio de vuelo</h1>
<p class="muted">Reserva {html.escape(pago['pnr'])} · vuelo {html.escape(pago['vuelo'])} · {html.escape(pago['fecha'])} {html.escape(pago['sale'])}</p>
<div class="total">USD {pago['total_usd']}</div><p class="muted">{html.escape(pago['detalle'])}</p>
<form method="post"><button type="submit">Pagar</button></form>""")

    @app.post("/pagar/{token}", response_class=HTMLResponse)
    def pagar(token: str):
        if not repo.obtener_pago(token):
            return _pagina("Enlace no válido", "<h1>Enlace no válido</h1>")
        repo.marcar_pagado(token)
        return ver_pago(token)

    # ---------- Administración de la demo --------------------------------------------

    @app.post("/admin/reiniciar", dependencies=[Depends(autenticar)])
    def reiniciar():
        repo.reiniciar(*cargar_semilla(cfg.dir_datos))
        return {"reiniciado": True}

    app.state.repo = repo
    return app


app = crear_app()
