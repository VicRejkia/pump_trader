import asyncio
import redis.asyncio as aioredis
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.exceptions import RequestValidationError
from fastapi.responses import PlainTextResponse
import strawberry
from strawberry.fastapi import GraphQLRouter

from bot_logger import logger
from api.endpoints import bot_control, config as api_config
from api.metrics import setup_metrics
from api.auth import auth_router
from core.bot_service import BotService
from core.database import DatabaseClient
from config.loader import ConfigLoader
from state_manager import GlobalState

# --- GraphQL Schema (Placeholder) ---
@strawberry.type
class Query:
    @strawberry.field
    def hello(self) -> str:
        return "Hello from the PumpTrader v3 API"

graphql_schema = strawberry.Schema(query=Query)
graphql_app = GraphQLRouter(graphql_schema)

# --- App Initialization ---
app = FastAPI(
    title="PumpTrader v3.0 C&C Hub",
    description="Central command server for the Solana trading bot.",
    version="3.0.0"
)

# --- App Lifecycle Events ---
@app.on_event("startup")
async def startup_event():
    """
    Handles application startup logic:
    1. Load configuration
    2. Initialize global state
    3. Connect to PostgreSQL and Redis
    4. Start the main BotService
    """
    logger.info("Server startup initiated...")
    try:
        # 1. Load config and initialize state
        state = GlobalState.get_instance()
        config_loader = ConfigLoader()
        config = await config_loader.load_config()
        state.config = config
        
        # 2. Connect to PostgreSQL
        db_client = DatabaseClient(config=config)
        await db_client.connect()
        await state.set_db_client(db_client)
        logger.info("PostgreSQL pool established.")
        
        # 3. Connect to Redis
        redis_host = config.get('REDIS_HOST', 'localhost')
        redis_port = config.get('REDIS_PORT', 6379)
        state.redis_client = aioredis.Redis(host=redis_host, port=redis_port, decode_responses=True)
        await state.redis_client.ping()
        logger.info(f"Redis connection established at {redis_host}:{redis_port}.")
        
        # 4. Initialize and start the BotService
        bot_service = BotService(state=state, config=config, db_client=db_client)
        app.state.bot_service = bot_service
        asyncio.create_task(bot_service.start(), name="bot_service_main")
        
        logger.info("✅ C&C Hub startup complete. BotService is running.")
        
    except aioredis.exceptions.ConnectionError as e:
        logger.critical(f"CRITICAL: Failed to connect to Redis at {redis_host}:{redis_port}. {e}")
        # In a real app, you might want to exit if Redis is essential
        # For now, we log and continue, but bot commands will fail.
    except Exception as e:
        logger.critical(f"CRITICAL: Error during C&C Hub startup: {e}", exc_info=True)
        # This is a fatal error, re-raise to stop the server
        raise e

@app.on_event("shutdown")
async def shutdown_event():
    """Handles graceful shutdown"""
    logger.info("Server shutdown initiated...")
    state = GlobalState.get_instance()
    
    if hasattr(app.state, 'bot_service'):
        await app.state.bot_service.stop()
        
    if state.redis_client:
        await state.redis_client.close()
        logger.info("Redis connection closed.")
        
    if state.db_client:
        await state.db_client.close()
        logger.info("PostgreSQL pool closed.")
        
    logger.info("✅ C&C Hub shutdown complete.")

# --- Error Handlers ---
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request, exc):
    logger.warning(f"Validation error for {request.url}: {exc}")
    return PlainTextResponse(str(exc), status_code=422)

# --- WebSocket Endpoint (Placeholder) ---
@app.websocket("/ws/updates")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    # This would be replaced by a real broadcaster system
    try:
        while True:
            await websocket.send_text(f"Message at {datetime.now()}")
            await asyncio.sleep(5)
    except WebSocketDisconnect:
        logger.info("WebSocket client disconnected.")
    except Exception as e:
        logger.warning(f"WebSocket error: {e}")
    finally:
        await websocket.close()

# --- Include Routers ---
setup_metrics(app) # 1. Prometheus /metrics
app.include_router(auth_router, prefix="/auth", tags=["Authentication"])
app.include_router(bot_control.router, prefix="/control", tags=["Bot Control"])
app.include_router(api_config.router, prefix="/config", tags=["Configuration"])
app.include_router(graphql_app, prefix="/graphql")

# Simple root endpoint
@app.get("/")
def read_root():
    return {"status": "PumpTrader v3.0 C&C Hub is running."}