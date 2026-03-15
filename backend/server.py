from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from main.apis.bucket.bucket_urls import router as bucket_router
from main.apis.chats.chat_urls import router as chats_router
from main.apis.history.history_urls import router as history_router
from main.apis.reasearch.research_urls import router as research_router
from main.apis.settings.settings_urls import router as settings_router
from main.apis.workspace.workspace_urls import router as workspace_router
from main.src.utils.core.task_schedular import scheduler

# Initilize the queue workers: queue system for entire application so add temprory non important task to background processing queue.


@asynccontextmanager
async def lifespan(app: FastAPI):
    # -------- SERVER START --------
    await scheduler.start()

    yield

    # -------- SERVER SHUTDOWN --------
    await scheduler.shutdown()


app = FastAPI(title="Research API", version="1.0.0", lifespan=lifespan)

# Include the scheme (http) and port. Add 127.0.0.1 as well if needed.
allowed_origins = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
]

# Register CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,  # or ["*"] for all origins (not recommended for production)
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


app.include_router(research_router)
app.include_router(workspace_router)
app.include_router(history_router)
app.include_router(chats_router)
app.include_router(bucket_router)
app.include_router(settings_router)

app.get("/health", tags=["health"])(lambda: {"status": "ok"})


if __name__ == "__main__":
    uvicorn.run("server:app", host="0.0.0.0", port=8000, workers=1)
