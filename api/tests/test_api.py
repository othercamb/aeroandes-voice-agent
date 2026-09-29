from datetime import datetime
from zoneinfo import ZoneInfo

import pytest
from fastapi.testclient import TestClient

from app.config import Config
from app.main import crear_app
from app.repositorio import RepositorioMemoria, cargar_semilla

SECRETO = "secreto-de-prueba"
H = {"X-Agent-Secret": SECRETO}
BOGOTA = ZoneInfo("America/Bogota")
HOY_DEMO = datetime(2026, 10, 13, 10, 0, tzinfo=BOGOTA)


def _cliente(reloj=lambda: HOY_DEMO):
    cfg = Config(almacenamiento="memoria", agent_tools_secret=SECRETO, demo_sms_to="",
                 twilio_account_sid="", twilio_auth_token="", twilio_from_number="",
                 url_publica="https://api.demo")
    repo = RepositorioMemoria(*cargar_semilla(cfg.dir_datos))
    return TestClient(crear_app(cfg, repo, reloj=reloj)), repo


@pytest.fixture
def cliente():
    return _cliente()


# ---------- Seguridad ------------------------------------------------------------

def test_sin_secreto_rechaza(cliente):
    c, _ = cliente
    r = c.post("/herramientas/consultar-reserva", json={"codigo_reserva": "K7Q2MX", "apellido": "Rojas"})
    assert r.status_code == 401


def test_secreto_incorrecto_rechaza(cliente):
    c, _ = cliente
    r = c.post("/herramientas/consultar-reserva", headers={"X-Agent-Secret": "otro"},
               json={"codigo_reserva": "K7Q2MX", "apellido": "Rojas"})
    assert r.status_code == 401


def test_apellido_equivocado_no_revela_la_reserva(cliente):
    c, _ = cliente
    r = c.post("/herramientas/consultar-reserva", headers=H,
               json={"codigo_reserva": "K7Q2MX", "apellido": "Perez"}).json()
    assert r["verificado"] is False
    assert "vuelo" not in r


def test_verificacion_tolera_mayusculas_espacios_y_tildes(cliente):
    c, _ = cliente
    r = c.post("/herramientas/consultar-reserva", headers=H,
               json={"codigo_reserva": " k7q2 mx ", "apellido": "rójas"}).json()
    assert r["verificado"] is True


@pytest.mark.parametrize("apellido", [
    "Abejero Rojas",          # transcripción real de la primera llamada ("apellido Rojas")
    "apellido Rojas",
    "Rojas.",
    "Valentina Rojas",
])
def test_apellido_tolera_ruido_de_la_transcripcion(cliente, apellido):
    c, _ = cliente
    r = c.post("/herramientas/consultar-reserva", headers=H,
               json={"codigo_reserva": "K7Q2MX", "apellido": apellido}).json()
    assert r["verificado"] is True


@pytest.mark.parametrize("apellido", ["Rodas", "Rojo", "de", ""])
def test_apellido_distinto_sigue_fallando(cliente, apellido):
    c, _ = cliente
    r = c.post("/herramientas/consultar-reserva", headers=H,
               json={"codigo_reserva": "K7Q2MX", "apellido": apellido}).json()
    assert r["verificado"] is False


def test_codigo_con_un_caracter_distinto_se_acepta_si_el_apellido_coincide(cliente):
    c, _ = cliente
    # Transcripción real de la segunda llamada: "N de mamá" en lugar de M.
    r = c.post("/herramientas/consultar-reserva", headers=H,
               json={"codigo_reserva": "K7Q2NX", "apellido": "Rojas"}).json()
    assert r["verificado"] is True
    assert r["codigo_reserva"] == "K7Q2MX"
    assert "K7Q2MX" in r["indicacion"]


def test_codigo_con_un_caracter_distinto_y_apellido_ajeno_falla(cliente):
    c, _ = cliente
    r = c.post("/herramientas/consultar-reserva", headers=H,
               json={"codigo_reserva": "K7Q2NX", "apellido": "Gomez"}).json()
    assert r["verificado"] is False


@pytest.mark.parametrize("codigo", ["AZQ2MX", "K7K2NX", "1K12NE"])
def test_codigo_con_dos_o_mas_errores_falla(cliente, codigo):
    c, _ = cliente
    r = c.post("/herramientas/consultar-reserva", headers=H,
               json={"codigo_reserva": codigo, "apellido": "Rojas"}).json()
    assert r["verificado"] is False


# ---------- Webhook de inicio ------------------------------------------------------

@pytest.mark.parametrize("caller,pais,voz", [
    ("+573104567890", "CO", "1ZhMG5ZZgJ6XpkOrB8Az"),
    ("+525512345678", "MX", "9Godp7dNohUvXk6qp0gS"),
    ("+5491145678901", "AR", "4wDRKlxcHNOFO5kBvE81"),
    ("+56912345678", "CL", "6Gr4AVmTax1pMJO0lHRK"),
    ("+51987654321", "PE", "ek0qR5Bu0N3aPdijsdae"),
    ("+14155550100", "CO", "1ZhMG5ZZgJ6XpkOrB8Az"),  # desconocido → Colombia
    (None, "CO", "1ZhMG5ZZgJ6XpkOrB8Az"),
])
def test_inicio_conversacion_elige_voz_por_pais(cliente, caller, pais, voz):
    c, _ = cliente
    r = c.post("/webhooks/inicio-conversacion", headers=H, json={"caller_id": caller}).json()
    assert r["type"] == "conversation_initiation_client_data"
    assert r["dynamic_variables"]["pais_codigo"] == pais
    assert r["conversation_config_override"]["tts"]["voice_id"] == voz


def test_inicio_conversacion_permite_forzar_pais(cliente):
    c, _ = cliente
    r = c.post("/webhooks/inicio-conversacion", headers=H, json={"pais": "ar"}).json()
    assert r["dynamic_variables"]["pais_codigo"] == "AR"


# ---------- Golden path ------------------------------------------------------------

def test_golden_path_completo(cliente):
    c, repo = cliente
    auth = {"codigo_reserva": "K7Q2MX", "apellido": "Rojas"}

    r = c.post("/herramientas/consultar-reserva", headers=H, json=auth).json()
    assert r["verificado"] and r["cambio"]["permitido"] and r["tarifa"] == "Clásica"
    assert r["vuelo"]["numero"] == "AN101" and r["vuelo"]["fecha"] == "2026-10-20"

    # El 21 está lleno (mañana y tarde): ofrece alternativas, primero las del 22.
    r = c.post("/herramientas/buscar-vuelos", headers=H, json={**auth, "fecha_deseada": "2026-10-21"}).json()
    assert set(r["vuelos_llenos_en_fecha_pedida"]) == {"AN101", "AN103"}
    assert r["son_alternativas_cercanas"] is True
    assert [(o["fecha"], o["numero"]) for o in r["opciones"][:2]] == [("2026-10-22", "AN101"), ("2026-10-22", "AN103")]

    # El 22 hay dos opciones con el total correcto según la política.
    r = c.post("/herramientas/buscar-vuelos", headers=H, json={**auth, "fecha_deseada": "2026-10-22"}).json()
    totales = {o["numero"]: o["total_a_pagar_usd"] for o in r["opciones"]}
    assert totales == {"AN101": 80, "AN103": 60}

    # Sin confirmación explícita no se ejecuta.
    r = c.post("/herramientas/cambiar-vuelo", headers=H,
               json={**auth, "vuelo_id": "AN103-2026-10-22", "confirmacion_cliente": False}).json()
    assert r["ejecutado"] is False and r["codigo"] == "FALTA_CONFIRMACION"

    cupos_antes_nuevo = repo.obtener_vuelo("AN103-2026-10-22")["cupos"]
    cupos_antes_viejo = repo.obtener_vuelo("AN101-2026-10-20")["cupos"]
    r = c.post("/herramientas/cambiar-vuelo", headers=H,
               json={**auth, "vuelo_id": "AN103-2026-10-22", "confirmacion_cliente": True}).json()
    assert r["ejecutado"] is True
    assert r["total_a_pagar_usd"] == 60
    assert r["enlace_pago_enviado"] is True
    assert repo.obtener_vuelo("AN103-2026-10-22")["cupos"] == cupos_antes_nuevo - 1
    assert repo.obtener_vuelo("AN101-2026-10-20")["cupos"] == cupos_antes_viejo + 1

    reserva = repo.obtener_reserva("K7Q2MX")
    assert (reserva["vuelo"], reserva["fecha"]) == ("AN103", "2026-10-22")

    # La página de pago existe y se puede pagar.
    token = next(iter(repo._pagos))
    assert "USD 60" in c.get(f"/pagar/{token}").text
    assert "Pago recibido" in c.post(f"/pagar/{token}").text


def test_reiniciar_devuelve_los_datos_al_estado_inicial(cliente):
    c, repo = cliente
    auth = {"codigo_reserva": "K7Q2MX", "apellido": "Rojas"}
    c.post("/herramientas/cambiar-vuelo", headers=H,
           json={**auth, "vuelo_id": "AN103-2026-10-22", "confirmacion_cliente": True})
    assert repo.obtener_reserva("K7Q2MX")["fecha"] == "2026-10-22"
    assert c.post("/admin/reiniciar", headers=H).json()["reiniciado"]
    assert repo.obtener_reserva("K7Q2MX")["fecha"] == "2026-10-20"


# ---------- Casos fuera del guion ---------------------------------------------------

def test_tarifa_basica_no_permite_cambios(cliente):
    c, _ = cliente
    auth = {"codigo_reserva": "H3LM9P", "apellido": "Gomez"}
    r = c.post("/herramientas/consultar-reserva", headers=H, json=auth).json()
    assert r["cambio"]["codigo"] == "TARIFA_NO_PERMITE_CAMBIOS"
    r = c.post("/herramientas/buscar-vuelos", headers=H, json={**auth, "fecha_deseada": "2026-10-19"}).json()
    assert r["permitido"] is False


def test_cancelacion_de_aerolinea_reprograma_sin_costo(cliente):
    c, _ = cliente
    auth = {"codigo_reserva": "F9CN3E", "apellido": "Martinez"}
    r = c.post("/herramientas/consultar-reserva", headers=H, json=auth).json()
    assert r["cambio"]["sin_cargo"] is True
    assert r["vuelo"]["motivo_cancelacion"]
    r = c.post("/herramientas/buscar-vuelos", headers=H, json={**auth, "fecha_deseada": "2026-10-17"}).json()
    assert r["opciones"] and all(o["total_a_pagar_usd"] == 0 for o in r["opciones"])


def test_cancelacion_respeta_ventana_de_7_dias(cliente):
    c, _ = cliente
    auth = {"codigo_reserva": "F9CN3E", "apellido": "Martinez"}
    r = c.post("/herramientas/buscar-vuelos", headers=H, json={**auth, "fecha_deseada": "2026-10-28"}).json()
    assert r["opciones"] == []


def test_checkin_realizado_requiere_asesor(cliente):
    c, _ = cliente
    r = c.post("/herramientas/consultar-reserva", headers=H,
               json={"codigo_reserva": "W2LB9N", "apellido": "Salazar"}).json()
    assert r["cambio"]["codigo"] == "CHECKIN_REALIZADO"
    assert r["cambio"]["requiere_asesor"] is True


def test_flex_no_paga_cargo_de_cambio(cliente):
    c, _ = cliente
    r = c.post("/herramientas/buscar-vuelos", headers=H,
               json={"codigo_reserva": "B4VW7G", "apellido": "Fernandez", "fecha_deseada": "2026-10-27"}).json()
    assert r["opciones"]
    assert all("cargo de cambio" not in o["detalle_cobro"] for o in r["opciones"])


def test_dos_pasajeros_pagan_cargo_por_cada_uno(cliente):
    c, _ = cliente
    r = c.post("/herramientas/buscar-vuelos", headers=H,
               json={"codigo_reserva": "C3YT7Q", "apellido": "Ramirez", "fecha_deseada": "2026-10-31"}).json()
    assert r["opciones"]
    for o in r["opciones"]:
        assert o["total_a_pagar_usd"] >= 100  # 2 × USD 50 como mínimo
        assert "por 2 pasajeros" in o["detalle_cobro"]


def test_cambio_dentro_de_3_horas_no_se_permite():
    antes_de_salir = datetime(2026, 10, 20, 5, 0, tzinfo=BOGOTA)  # AN101 sale 07:10
    c, _ = _cliente(reloj=lambda: antes_de_salir)
    r = c.post("/herramientas/consultar-reserva", headers=H,
               json={"codigo_reserva": "K7Q2MX", "apellido": "Rojas"}).json()
    assert r["cambio"]["codigo"] == "FUERA_DE_PLAZO"


# ---------- Equipaje ---------------------------------------------------------------

def test_estado_de_equipaje(cliente):
    c, _ = cliente
    r = c.post("/herramientas/estado-equipaje", headers=H,
               json={"referencia": "sclan00482", "apellido": "Soto"}).json()
    assert r["encontrado"] and r["estado"] == "EN_BUSQUEDA"


def test_estado_de_equipaje_con_apellido_equivocado(cliente):
    c, _ = cliente
    r = c.post("/herramientas/estado-equipaje", headers=H,
               json={"referencia": "SCLAN00482", "apellido": "Rojas"}).json()
    assert r["encontrado"] is False and "estado" not in r
