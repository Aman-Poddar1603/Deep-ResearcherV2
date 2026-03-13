import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from main.apis.history.history_urls import router as history_router
from main.apis.reasearch.research_urls import router as research_router
from main.apis.workspace.workspace_urls import router as workspace_router

app = FastAPI(title="Research API", version="1.0.0")

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

app.get("/health", tags=["health"])(lambda: {"status": "ok"})


if __name__ == "__main__":
    uvicorn.run("server:app", host="0.0.0.0", port=8000, workers=1)
