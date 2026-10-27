"""FastAPI app lifecycle and shared HTTP middleware."""
from contextlib import asynccontextmanager
import logging
import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.api.routes import router
from backend.config import settings
from backend.trading.runtime import broker, engine

from backend.utils.logger import configure_logging
configure_logging(settings.log_level)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    connected = False
    if os.getenv("AI_TRADING_SKIP_MT5_INIT") != "1":
      try:
        broker.connect()
        connected = True
        engine.start_worker()
        logger.info("MT5 connected; worker ready in STOP state")
      except Exception:
        logger.exception("MT5 initialization failed; API is available in disconnected mode")
    else:
        logger.info("Skipping MT5 startup because AI_TRADING_SKIP_MT5_INIT=1")
    app.state.mt5_connected = connected
    yield
    engine.shutdown()
    if connected:
        broker.shutdown()
    logger.info("Backend shutdown complete")


app = FastAPI(title="AI Trading API", version="1.0.0", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173", "http://localhost:8080"],
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type", "Authorization"],
)
app.include_router(router)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend.main:app", host=settings.api_host, port=settings.api_port, log_level=settings.log_level.lower())

