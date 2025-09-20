from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from typing import List, Optional
from datetime import time, datetime
from app.core.database import get_db
from app.modules.access.models import Access
from app.modules.users.models import User
from app.modules.room.models import Room
from pydantic import BaseModel

router = APIRouter(prefix="/access", tags=["access"])


class AccessCreate(BaseModel):
    user_id: int
    room_id: int
    from_hour: Optional[time] = None
    to_hour: Optional[time] = None
    all_time_access: bool = False


class AccessUpdate(BaseModel):
    room_id: int
    from_hour: Optional[time] = None
    to_hour: Optional[time] = None
    all_time_access: bool = False


class AccessResponse(BaseModel):
    id: int
    user_id: int
    room_id: int
    from_hour: Optional[time]
    to_hour: Optional[time]
    all_time_access: bool

    class Config:
        from_attributes = True


class CanUnlockResponse(BaseModel):
    can_unlock: bool
    message: str


@router.post("/", response_model=AccessResponse)
async def create_access(access: AccessCreate, db: AsyncSession = Depends(get_db)):
    # Check if user exists
    user_result = await db.execute(select(User).where(User.id == access.user_id))
    if not user_result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="User not found")

    # Check if room exists
    room_result = await db.execute(select(Room).where(Room.id == access.room_id))
    if not room_result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Room not found")

    # Check if user already has access (only one row per user allowed)
    existing_access = await db.execute(select(Access).where(Access.user_id == access.user_id))
    if existing_access.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="User already has access configured. Update existing access instead.")

    # Validate time fields if not all_time_access
    if not access.all_time_access and (access.from_hour is None or access.to_hour is None):
        raise HTTPException(status_code=400, detail="from_hour and to_hour are required when all_time_access is False")

    db_access = Access(
        user_id=access.user_id,
        room_id=access.room_id,
        from_hour=access.from_hour,
        to_hour=access.to_hour,
        all_time_access=access.all_time_access
    )
    db.add(db_access)
    await db.commit()
    await db.refresh(db_access)
    return db_access


@router.get("/", response_model=List[AccessResponse])
async def get_access_list(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Access))
    access_list = result.scalars().all()
    return access_list


@router.get("/{access_id}", response_model=AccessResponse)
async def get_access(access_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Access).where(Access.id == access_id))
    access = result.scalar_one_or_none()
    if not access:
        raise HTTPException(status_code=404, detail="Access not found")
    return access


@router.get("/user/{user_id}", response_model=AccessResponse)
async def get_user_access(user_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Access).where(Access.user_id == user_id))
    access = result.scalar_one_or_none()
    if not access:
        raise HTTPException(status_code=404, detail="Access not found for this user")
    return access


@router.put("/user/{user_id}", response_model=AccessResponse)
async def update_user_access(user_id: int, access_update: AccessUpdate, db: AsyncSession = Depends(get_db)):
    # Check if room exists
    room_result = await db.execute(select(Room).where(Room.id == access_update.room_id))
    if not room_result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Room not found")

    result = await db.execute(select(Access).where(Access.user_id == user_id))
    access = result.scalar_one_or_none()
    if not access:
        raise HTTPException(status_code=404, detail="Access not found for this user")

    # Validate time fields if not all_time_access
    if not access_update.all_time_access and (access_update.from_hour is None or access_update.to_hour is None):
        raise HTTPException(status_code=400, detail="from_hour and to_hour are required when all_time_access is False")

    access.room_id = access_update.room_id
    access.from_hour = access_update.from_hour
    access.to_hour = access_update.to_hour
    access.all_time_access = access_update.all_time_access
    await db.commit()
    await db.refresh(access)
    return access


@router.delete("/user/{user_id}")
async def delete_user_access(user_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Access).where(Access.user_id == user_id))
    access = result.scalar_one_or_none()
    if not access:
        raise HTTPException(status_code=404, detail="Access not found for this user")

    await db.delete(access)
    await db.commit()
    return {"message": "Access deleted successfully"}


@router.get("/check-unlock/{user_id}/{room_id}", response_model=CanUnlockResponse)
async def check_can_unlock(user_id: int, room_id: int, db: AsyncSession = Depends(get_db)):
    # Get user access for the specific room
    result = await db.execute(
        select(Access).where(
            and_(Access.user_id == user_id, Access.room_id == room_id)
        )
    )
    access = result.scalar_one_or_none()

    if not access:
        return CanUnlockResponse(
            can_unlock=False,
            message="User does not have access to this room"
        )

    # If user has all_time_access, they can always unlock
    if access.all_time_access:
        return CanUnlockResponse(
            can_unlock=True,
            message="User has all-time access to this room"
        )

    # Check time-based access
    if access.from_hour is None or access.to_hour is None:
        return CanUnlockResponse(
            can_unlock=False,
            message="Access time configuration is invalid"
        )

    # Check current time
    current_time = datetime.now().time()

    # Handle time range that crosses midnight
    if access.from_hour <= access.to_hour:
        # Normal range (e.g., 9:00 to 17:00)
        can_unlock = access.from_hour <= current_time <= access.to_hour
    else:
        # Range crosses midnight (e.g., 22:00 to 06:00)
        can_unlock = current_time >= access.from_hour or current_time <= access.to_hour

    if can_unlock:
        return CanUnlockResponse(
            can_unlock=True,
            message=f"User can unlock room from {access.from_hour} to {access.to_hour}"
        )
    else:
        return CanUnlockResponse(
            can_unlock=False,
            message=f"Current time {current_time} is outside allowed access hours ({access.from_hour} to {access.to_hour})"
        )