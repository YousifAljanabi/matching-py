from fastapi import FastAPI
from app.modules.users.router import router as users_router
from app.modules.room.router import router as rooms_router
from app.modules.access.router import router as access_router
from app.modules.log.router import router as logs_router

app = FastAPI(title="Home Security API", version="1.0.0")

# Include all routers
app.include_router(users_router)
app.include_router(rooms_router)
app.include_router(access_router)
app.include_router(logs_router)


@app.get("/")
async def root():
    return {"message": "Home Security API is running"}