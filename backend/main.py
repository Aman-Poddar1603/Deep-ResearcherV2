from fastapi import FastAPI
import uvicorn
from main.apis.bucket.bucket_urls import router as bucket_router
from main.apis.chats.chat_urls import router as chats_router
from main.apis.history.history_urls import router as history_router
from main.apis.reasearch.research_urls import router as research_router
from main.apis.settings.settings_urls import router as settings_router
from main.apis.workspace.workspace_urls import router as workspace_router

app = FastAPI(title="Research API", version="1.0.0")

app.include_router(research_router)
app.include_router(workspace_router)
app.include_router(history_router)
app.include_router(chats_router)
app.include_router(bucket_router)
app.include_router(settings_router)

app.get("/health", tags=["health"])(lambda: {"status": "ok"})


if __name__ == "__main__":
    uvicorn.run(app, host="localhost", port=8000, workers=5)
