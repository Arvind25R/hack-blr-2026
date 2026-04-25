from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routers.process import router as process_router

app = FastAPI(title="Service B", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(process_router)


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "healthy", "service": "service-b"}