import os
from contextlib import asynccontextmanager
from pathlib import Path
from typing import List, Optional
from fastapi import FastAPI, HTTPException, Query, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from config.config import settings
from src.database.connection import init_db
from src.database.models import (
    CameraStatus, CameraWithStatus, SystemSummary, CheckLog
)
from src.database.repository import CameraRepository, LogRepository

@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield

app = FastAPI(
    title="Camera Checker Monitoring API",
    description="API para monitoreo y visualización de estado de cámaras de seguridad",
    version="1.0.0",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/api/summary", response_model=SystemSummary, tags=["Monitoring"])
def get_summary():
    """Retorna un resumen global de salud y métricas de todas las cámaras."""
    return CameraRepository.get_system_summary()

@app.get("/api/cameras", response_model=List[CameraWithStatus], tags=["Monitoring"])
def get_cameras(
    status_filter: Optional[CameraStatus] = Query(None, alias="status", description="Filtrar por estado"),
    search: Optional[str] = Query(None, description="Buscar por nombre o dirección IP/URL"),
    enabled_only: Optional[bool] = Query(None, alias="enabled", description="Filtrar por activas/pausadas")
):
    """Retorna la lista de cámaras con su estado más reciente y detalles de grabación."""
    cameras = CameraRepository.get_cameras_with_latest_status()
    
    # Filtro por estado
    if status_filter:
        cameras = [c for c in cameras if c.status == status_filter]
        
    # Filtro por activas/desactivadas
    if enabled_only is not None:
        cameras = [c for c in cameras if c.enabled == enabled_only]
        
    # Filtro por texto de búsqueda
    if search:
        s_lower = search.lower().strip()
        cameras = [
            c for c in cameras 
            if s_lower in c.name.lower() or s_lower in c.ip_or_url.lower() or (c.details and s_lower in c.details.lower())
        ]
        
    return cameras

@app.get("/api/cameras/{camera_id}", response_model=CameraWithStatus, tags=["Monitoring"])
def get_camera_detail(camera_id: int):
    """Retorna el estado detallado de una cámara específica."""
    cameras = CameraRepository.get_cameras_with_latest_status()
    cam = next((c for c in cameras if c.id == camera_id), None)
    if not cam:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Cámara #{camera_id} no encontrada")
    return cam

@app.get("/api/logs", response_model=List[CheckLog], tags=["Audit Logs"])
def get_check_logs(
    limit: int = Query(50, ge=1, le=500, description="Número de registros a retornar"),
    camera_id: Optional[int] = Query(None, description="Filtrar logs por ID de cámara")
):
    """Retorna el historial de logs de chequeo."""
    logs = LogRepository.get_recent_logs(limit=limit)
    if camera_id is not None:
        logs = [l for l in logs if l.camera_id == camera_id]
    return logs

@app.get("/api/screenshots/{filename}", tags=["Evidence"])
def get_screenshot_file(filename: str):
    """Descarga o visualiza una captura de evidencia tomada durante las verificaciones."""
    # Sanitizar para evitar Directory Traversal
    safe_filename = Path(filename).name
    screenshot_path = settings.SCREENSHOT_DIR / safe_filename
    
    if not screenshot_path.exists() or not screenshot_path.is_file():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, 
            detail=f"Captura de evidencia '{safe_filename}' no encontrada"
        )
    
    return FileResponse(
        path=str(screenshot_path),
        media_type="image/png",
        headers={"Cache-Control": "public, max-age=3600"}
    )

# Montar frontend estático si el directorio existe
FRONTEND_DIR = settings.BASE_DIR / "src" / "web" / "frontend"
if not FRONTEND_DIR.exists():
    FRONTEND_DIR = settings.BASE_DIR / "frontend"

if FRONTEND_DIR.exists():
    app.mount("/", StaticFiles(directory=str(FRONTEND_DIR), html=True), name="frontend")
