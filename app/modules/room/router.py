from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List
from app.core.database import get_db
from app.modules.room.models import Room, RoomState
from pydantic import BaseModel

router = APIRouter(prefix="/rooms", tags=["rooms"])


class RoomCreate(BaseModel):
    name: str
    state: RoomState = RoomState.UNLOCKED


class RoomUpdate(BaseModel):
    name: str = None
    state: RoomState = None


class RoomResponse(BaseModel):
    id: int
    name: str
    state: RoomState

    class Config:
        from_attributes = True


@router.post("/", response_model=RoomResponse)
async def create_room(room: RoomCreate, db: AsyncSession = Depends(get_db)):
    db_room = Room(name=room.name, state=room.state)
    db.add(db_room)
    await db.commit()
    await db.refresh(db_room)
    return db_room


@router.get("/", response_model=List[RoomResponse])
async def get_rooms(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Room))
    rooms = result.scalars().all()
    return rooms


@router.get("/{room_id}", response_model=RoomResponse)
async def get_room(room_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Room).where(Room.id == room_id))
    room = result.scalar_one_or_none()
    if not room:
        raise HTTPException(status_code=404, detail="Room not found")
    return room


@router.get("/name/{room_name}", response_model=RoomResponse)
async def get_room_by_name(room_name: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Room).where(Room.name == room_name))
    room = result.scalar_one_or_none()
    if not room:
        raise HTTPException(status_code=404, detail="Room not found")
    return room


@router.put("/{room_id}", response_model=RoomResponse)
async def update_room(room_id: int, room_update: RoomUpdate, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Room).where(Room.id == room_id))
    room = result.scalar_one_or_none()
    if not room:
        raise HTTPException(status_code=404, detail="Room not found")

    if room_update.name is not None:
        room.name = room_update.name
    if room_update.state is not None:
        room.state = room_update.state

    await db.commit()
    await db.refresh(room)
    return room


@router.delete("/{room_id}")
async def delete_room(room_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Room).where(Room.id == room_id))
    room = result.scalar_one_or_none()
    if not room:
        raise HTTPException(status_code=404, detail="Room not found")

    await db.delete(room)
    await db.commit()
    return {"message": "Room deleted successfully"}