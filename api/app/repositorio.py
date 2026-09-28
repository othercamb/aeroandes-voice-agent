"""Acceso a datos: una interfaz, dos implementaciones.

- RepositorioMemoria: para desarrollo local y tests; se siembra desde data/*.json.
- RepositorioFirestore: para Cloud Run. El cambio de vuelo corre en una transacción
  para que dos llamadas simultáneas no vendan el mismo cupo.
"""
import copy
import json
import threading
from abc import ABC, abstractmethod
from pathlib import Path


class SinCupoError(Exception):
    pass


def cargar_semilla(dir_datos: Path) -> tuple[list[dict], list[dict]]:
    vuelos = json.loads((dir_datos / "vuelos.json").read_text())
    reservas = json.loads((dir_datos / "reservas.json").read_text())
    return vuelos, reservas


def _reclamos_desde(reservas: list[dict]) -> dict[str, dict]:
    reclamos = {}
    for r in reservas:
        rec = r.get("reclamo_equipaje")
        if rec:
            reclamos[rec["referencia"]] = {**rec, "pnr": r["pnr"]}
    return reclamos


class Repositorio(ABC):
    @abstractmethod
    def obtener_reserva(self, pnr: str) -> dict | None: ...

    @abstractmethod
    def obtener_vuelo(self, vuelo_id: str) -> dict | None: ...

    @abstractmethod
    def vuelos_ruta(self, origen: str, destino: str, desde: str, hasta: str) -> list[dict]: ...

    @abstractmethod
    def aplicar_cambio(self, pnr: str, vuelo_nuevo_id: str, evento: dict) -> dict: ...

    @abstractmethod
    def obtener_reclamo(self, referencia: str) -> dict | None: ...

    @abstractmethod
    def guardar_pago(self, token: str, pago: dict) -> None: ...

    @abstractmethod
    def obtener_pago(self, token: str) -> dict | None: ...

    @abstractmethod
    def marcar_pagado(self, token: str) -> None: ...

    @abstractmethod
    def reiniciar(self, vuelos: list[dict], reservas: list[dict]) -> None: ...


class RepositorioMemoria(Repositorio):
    def __init__(self, vuelos: list[dict], reservas: list[dict]):
        self._lock = threading.Lock()
        self.reiniciar(vuelos, reservas)

    def reiniciar(self, vuelos, reservas):
        with self._lock:
            self._vuelos = {v["id"]: copy.deepcopy(v) for v in vuelos}
            self._reservas = {r["pnr"]: copy.deepcopy(r) for r in reservas}
            self._reclamos = _reclamos_desde(reservas)
            self._pagos: dict[str, dict] = {}

    def obtener_reserva(self, pnr):
        r = self._reservas.get(pnr)
        return copy.deepcopy(r) if r else None

    def obtener_vuelo(self, vuelo_id):
        v = self._vuelos.get(vuelo_id)
        return copy.deepcopy(v) if v else None

    def vuelos_ruta(self, origen, destino, desde, hasta):
        return sorted(
            (copy.deepcopy(v) for v in self._vuelos.values()
             if v["origen"] == origen and v["destino"] == destino and desde <= v["fecha"] <= hasta),
            key=lambda v: (v["fecha"], v["sale"]),
        )

    def aplicar_cambio(self, pnr, vuelo_nuevo_id, evento):
        with self._lock:
            reserva = self._reservas[pnr]
            nuevo = self._vuelos[vuelo_nuevo_id]
            n = len(reserva["pasajeros"])
            if nuevo["cupos"] < n:
                raise SinCupoError(vuelo_nuevo_id)
            anterior = self._vuelos.get(f'{reserva["vuelo"]}-{reserva["fecha"]}')
            nuevo["cupos"] -= n
            if anterior and anterior["estado"] == "PROGRAMADO":
                anterior["cupos"] += n
            reserva["vuelo"], reserva["fecha"] = nuevo["vuelo"], nuevo["fecha"]
            reserva["estado"] = "CONFIRMADA"
            reserva.setdefault("historial", []).append(evento)
            return copy.deepcopy(reserva)

    def obtener_reclamo(self, referencia):
        r = self._reclamos.get(referencia)
        return copy.deepcopy(r) if r else None

    def guardar_pago(self, token, pago):
        self._pagos[token] = copy.deepcopy(pago)

    def obtener_pago(self, token):
        p = self._pagos.get(token)
        return copy.deepcopy(p) if p else None

    def marcar_pagado(self, token):
        if token in self._pagos:
            self._pagos[token]["estado"] = "PAGADO"


class RepositorioFirestore(Repositorio):
    def __init__(self, project_id: str, database: str = "(default)"):
        from google.cloud import firestore  # import diferido: no se necesita en tests

        self._fs = firestore
        self._db = firestore.Client(project=project_id or None, database=database)
        self._vuelos = self._db.collection("vuelos")
        self._reservas = self._db.collection("reservas")
        self._reclamos = self._db.collection("reclamos_equipaje")
        self._pagos = self._db.collection("pagos")

    def obtener_reserva(self, pnr):
        d = self._reservas.document(pnr).get()
        return d.to_dict() if d.exists else None

    def obtener_vuelo(self, vuelo_id):
        d = self._vuelos.document(vuelo_id).get()
        return d.to_dict() if d.exists else None

    def vuelos_ruta(self, origen, destino, desde, hasta):
        from google.cloud.firestore_v1.base_query import FieldFilter

        q = (self._vuelos
             .where(filter=FieldFilter("origen", "==", origen))
             .where(filter=FieldFilter("destino", "==", destino)))
        # El filtro por fecha se hace en memoria para no exigir un índice compuesto:
        # son pocos documentos por ruta.
        vuelos = [d.to_dict() for d in q.stream()]
        vuelos = [v for v in vuelos if desde <= v["fecha"] <= hasta]
        return sorted(vuelos, key=lambda v: (v["fecha"], v["sale"]))

    def aplicar_cambio(self, pnr, vuelo_nuevo_id, evento):
        transaccion = self._db.transaction()
        ref_reserva = self._reservas.document(pnr)
        ref_nuevo = self._vuelos.document(vuelo_nuevo_id)

        @self._fs.transactional
        def _cambiar(tx):
            reserva = ref_reserva.get(transaction=tx).to_dict()
            nuevo = ref_nuevo.get(transaction=tx).to_dict()
            ref_anterior = self._vuelos.document(f'{reserva["vuelo"]}-{reserva["fecha"]}')
            snap_anterior = ref_anterior.get(transaction=tx)
            n = len(reserva["pasajeros"])
            if nuevo["cupos"] < n:
                raise SinCupoError(vuelo_nuevo_id)
            tx.update(ref_nuevo, {"cupos": nuevo["cupos"] - n})
            if snap_anterior.exists and snap_anterior.get("estado") == "PROGRAMADO":
                tx.update(ref_anterior, {"cupos": snap_anterior.get("cupos") + n})
            reserva.update({"vuelo": nuevo["vuelo"], "fecha": nuevo["fecha"], "estado": "CONFIRMADA"})
            reserva.setdefault("historial", []).append(evento)
            tx.set(ref_reserva, reserva)
            return reserva

        return _cambiar(transaccion)

    def obtener_reclamo(self, referencia):
        d = self._reclamos.document(referencia).get()
        return d.to_dict() if d.exists else None

    def guardar_pago(self, token, pago):
        self._pagos.document(token).set(pago)

    def obtener_pago(self, token):
        d = self._pagos.document(token).get()
        return d.to_dict() if d.exists else None

    def marcar_pagado(self, token):
        self._pagos.document(token).update({"estado": "PAGADO"})

    def reiniciar(self, vuelos, reservas):
        """Vuelve los datos al estado inicial (útil entre ensayos de la demo)."""
        for col in (self._vuelos, self._reservas, self._reclamos, self._pagos):
            for d in col.list_documents():
                d.delete()
        lote = self._db.batch()
        ops = 0
        for v in vuelos:
            lote.set(self._vuelos.document(v["id"]), v)
            ops += 1
            if ops == 400:
                lote.commit()
                lote, ops = self._db.batch(), 0
        for r in reservas:
            lote.set(self._reservas.document(r["pnr"]), r)
        for ref, rec in _reclamos_desde(reservas).items():
            lote.set(self._reclamos.document(ref), rec)
        lote.commit()
