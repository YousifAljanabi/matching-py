from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.modules.users.router import router as users_router
from app.modules.room.router import router as rooms_router
from app.modules.access.router import router as access_router
from app.modules.log.router import router as logs_router
from app.modules.normalize_phone.pipeline import router as pipeline_router

app = FastAPI(title="Home Security API", version="1.0.0")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all origins
    allow_credentials=True,
    allow_methods=["*"],  # Allows all methods
    allow_headers=["*"],  # Allows all headers
)

# Include all routers
app.include_router(users_router)
app.include_router(rooms_router)
app.include_router(access_router)
app.include_router(logs_router)
app.include_router(pipeline_router)


@app.get("/")
async def root():
    return {"message": "Home Security API is running"}