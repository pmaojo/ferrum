"""Endpoints de diagnóstico optométrico (demo).

Proporciona:
  GET /diagnosis/{id}           -> Recupera un diagnóstico conocido.
  POST /diagnosis/infer         -> Inferencia rápida a partir de medidas (CSV o lista).

Se mantiene fuera del prefijo /api para que el cliente Rust existente
(`GraphClient.fetch_diagnosis`) funcione sin cambios.
"""
from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import List

router = APIRouter()


class DiagnosisModel(BaseModel):
    id: str = Field(..., max_length=100)
    description: str = Field(..., max_length=500)


# Catálogo simple (mock). En un futuro se puede leer de Falkor / Ontología.
_CATALOG = {
    "myopia": "Myopia (Near-sightedness)",
    "hyperopia": "Hyperopia (Far-sightedness)",
    "astigmatism": "Astigmatism",
}


@router.get("/diagnosis/{id}", response_model=DiagnosisModel)
async def get_diagnosis(id: str) -> DiagnosisModel:
    if id in _CATALOG:
        return DiagnosisModel(id=id, description=_CATALOG[id])
    # Permite devolver un diagnóstico dinámico 'generated'
    if id == "generated":
        return DiagnosisModel(id="generated", description="Generic refractive status")
    raise HTTPException(status_code=404, detail="Diagnosis not found")


class MeasurementsPayload(BaseModel):
    measurements: str | List[float]


@router.post("/diagnosis/infer", response_model=DiagnosisModel)
async def infer_diagnosis(payload: MeasurementsPayload) -> DiagnosisModel:
    if isinstance(payload.measurements, str):
        values = [v for v in (s.strip() for s in payload.measurements.split(",")) if v]
        floats = [float(v) for v in values if _is_float(v)]
    else:
        floats = payload.measurements
    if not floats:
        raise HTTPException(status_code=400, detail="No measurements provided")
    avg = sum(floats) / len(floats)
    if avg < 0:
        return DiagnosisModel(id="myopia", description=_CATALOG["myopia"])
    else:
        return DiagnosisModel(id="hyperopia", description=_CATALOG["hyperopia"])


def _is_float(s: str) -> bool:
    try:
        float(s)
        return True
    except ValueError:
        return False
