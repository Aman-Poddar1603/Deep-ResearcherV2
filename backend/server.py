from fastapi import FastAPI
import uvicorn
from main.apis.reasearch.research_urls import router as research_router

app = FastAPI(title="Research API", version="1.0.0")

app.include_router(research_router)

app.get("/health", tags=["health"])(lambda: {"status": "ok"})


if __name__ == "__main__":
    uvicorn.run("server:app", host="0.0.0.0", port=8000, workers=1)
