import uvicorn
from config.config import settings
from src.utils.logger import logger

def start_server(host: str = "0.0.0.0", port: int = 8000, reload: bool = False):
    """Inicia el servidor web FastAPI con Uvicorn."""
    logger.info("Iniciando Camera Checker API & Dashboard en http://%s:%s ...", host if host != "0.0.0.0" else "localhost", port)
    uvicorn.run("src.api.app:app", host=host, port=port, reload=reload)

if __name__ == "__main__":
    start_server(host="0.0.0.0", port=8000, reload=True)
