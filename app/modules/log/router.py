from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from typing import List
from datetime import datetime
from app.core.database import get_db
from app.modules.log.models import Log
from app.modules.users.models import User
from app.modules.room.models import Room
from pydantic import BaseModel

router = APIRouter(prefix="/logs", tags=["logs"])


class LogCreate(BaseModel):
    datetime: datetime
    user_id: int
    room_id: int


class LogResponse(BaseModel):
    id: int
    datetime: datetime
    user_id: int
    room_id: int

    class Config:
        from_attributes = True


class LogDetailResponse(BaseModel):
    id: int
    datetime: datetime
    user_id: int
    user_name: str
    room_id: int
    room_name: str

    class Config:
        from_attributes = True


@router.post("/", response_model=LogResponse)
async def create_log(log: LogCreate, db: AsyncSession = Depends(get_db)):
    # Check if user exists
    user_result = await db.execute(select(User).where(User.id == log.user_id))
    if not user_result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="User not found")

    # Check if room exists
    room_result = await db.execute(select(Room).where(Room.id == log.room_id))
    if not room_result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Room not found")

    db_log = Log(
        datetime=log.datetime,
        user_id=log.user_id,
        room_id=log.room_id
    )
    db.add(db_log)
    await db.commit()
    await db.refresh(db_log)
    return db_log


@router.get("/", response_model=List[LogDetailResponse])
async def get_all_logs(db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Log, User.name.label("user_name"), Room.name.label("room_name"))
        .join(User, Log.user_id == User.id)
        .join(Room, Log.room_id == Room.id)
        .order_by(Log.datetime.desc())
    )

    logs = []
    for log, user_name, room_name in result.all():
        logs.append(LogDetailResponse(
            id=log.id,
            datetime=log.datetime,
            user_id=log.user_id,
            user_name=user_name,
            room_id=log.room_id,
            room_name=room_name
        ))

    return logs


@router.get("/room/{room_id}", response_model=List[LogDetailResponse])
async def get_logs_by_room_id(room_id: int, db: AsyncSession = Depends(get_db)):
    # Check if room exists
    room_result = await db.execute(select(Room).where(Room.id == room_id))
    room = room_result.scalar_one_or_none()
    if not room:
        raise HTTPException(status_code=404, detail="Room not found")

    result = await db.execute(
        select(Log, User.name.label("user_name"), Room.name.label("room_name"))
        .join(User, Log.user_id == User.id)
        .join(Room, Log.room_id == Room.id)
        .where(Log.room_id == room_id)
        .order_by(Log.datetime.desc())
    )

    logs = []
    for log, user_name, room_name in result.all():
        logs.append(LogDetailResponse(
            id=log.id,
            datetime=log.datetime,
            user_id=log.user_id,
            user_name=user_name,
            room_id=log.room_id,
            room_name=room_name
        ))

    return logs


@router.get("/room/name/{room_name}", response_model=List[LogDetailResponse])
async def get_logs_by_room_name(room_name: str, db: AsyncSession = Depends(get_db)):
    # Check if room exists
    room_result = await db.execute(select(Room).where(Room.name == room_name))
    room = room_result.scalar_one_or_none()
    if not room:
        raise HTTPException(status_code=404, detail="Room not found")

    result = await db.execute(
        select(Log, User.name.label("user_name"), Room.name.label("room_name"))
        .join(User, Log.user_id == User.id)
        .join(Room, Log.room_id == Room.id)
        .where(Room.name == room_name)
        .order_by(Log.datetime.desc())
    )

    logs = []
    for log, user_name, room_name in result.all():
        logs.append(LogDetailResponse(
            id=log.id,
            datetime=log.datetime,
            user_id=log.user_id,
            user_name=user_name,
            room_id=log.room_id,
            room_name=room_name
        ))

    return logs


@router.get("/{log_id}", response_model=LogDetailResponse)
async def get_log(log_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Log, User.name.label("user_name"), Room.name.label("room_name"))
        .join(User, Log.user_id == User.id)
        .join(Room, Log.room_id == Room.id)
        .where(Log.id == log_id)
    )

    log_data = result.first()
    if not log_data:
        raise HTTPException(status_code=404, detail="Log not found")

    log, user_name, room_name = log_data
    return LogDetailResponse(
        id=log.id,
        datetime=log.datetime,
        user_id=log.user_id,
        user_name=user_name,
        room_id=log.room_id,
        room_name=room_name
    )