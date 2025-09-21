from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from typing import List, Optional
from datetime import time, datetime
from app.core.database import get_db
from app.modules.access.models import Access
from app.modules.users.models import User
from app.modules.room.models import Room, RoomState
from pydantic import BaseModel

router = APIRouter(prefix="/access", tags=["access"])


class AccessCreate(BaseModel):
    user_name: str
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
    user_name: str
    room_id: int
    room_name: str
    from_hour: Optional[time]
    to_hour: Optional[time]
    all_time_access: bool

    class Config:
        from_attributes = True


class CanAccessResponse(BaseModel):
    can_access: bool
    message: str


@router.post("/", response_model=AccessResponse)
async def upsert_access(access: AccessCreate, db: AsyncSession = Depends(get_db)):
    user_result = await db.execute(select(User).where(User.name == access.user_name))
    user = user_result.scalar_one_or_none()

    if not user:
        user = User(name=access.user_name)
        db.add(user)
        await db.commit()
        await db.refresh(user)

    # Check if room exists
    room_result = await db.execute(select(Room).where(Room.id == access.room_id))
    if not room_result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Room not found")

    # Validate time fields if not all_time_access
    if not access.all_time_access and (access.from_hour is None or access.to_hour is None):
        raise HTTPException(status_code=400, detail="from_hour and to_hour are required when all_time_access is False")

    # Check if user already has access (only one row per user allowed)
    existing_access_result = await db.execute(select(Access).where(Access.user_id == user.id))
    existing_access = existing_access_result.scalar_one_or_none()

    # Get room details for response
    room_result = await db.execute(select(Room).where(Room.id == access.room_id))
    room = room_result.scalar_one()

    if existing_access:
        # Update existing access
        existing_access.room_id = access.room_id
        existing_access.from_hour = access.from_hour
        existing_access.to_hour = access.to_hour
        existing_access.all_time_access = access.all_time_access
        await db.commit()
        await db.refresh(existing_access)

        return AccessResponse(
            id=existing_access.id,
            user_id=existing_access.user_id,
            user_name=user.name,
            room_id=existing_access.room_id,
            room_name=room.name,
            from_hour=existing_access.from_hour,
            to_hour=existing_access.to_hour,
            all_time_access=existing_access.all_time_access
        )
    else:
        # Create new access
        db_access = Access(
            user_id=user.id,
            room_id=access.room_id,
            from_hour=access.from_hour,
            to_hour=access.to_hour,
            all_time_access=access.all_time_access
        )
        db.add(db_access)
        await db.commit()
        await db.refresh(db_access)

        return AccessResponse(
            id=db_access.id,
            user_id=db_access.user_id,
            user_name=user.name,
            room_id=db_access.room_id,
            room_name=room.name,
            from_hour=db_access.from_hour,
            to_hour=db_access.to_hour,
            all_time_access=db_access.all_time_access
        )


@router.get("/", response_model=List[AccessResponse])
async def get_access_list(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Access, User, Room).join(User).join(Room))
    access_list = []
    for access, user, room in result.all():
        access_list.append(AccessResponse(
            id=access.id,
            user_id=access.user_id,
            user_name=user.name,
            room_id=access.room_id,
            room_name=room.name,
            from_hour=access.from_hour,
            to_hour=access.to_hour,
            all_time_access=access.all_time_access
        ))
    return access_list


@router.get("/{access_id}", response_model=AccessResponse)
async def get_access(access_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Access, User, Room).join(User).join(Room).where(Access.id == access_id))
    access_data = result.first()
    if not access_data:
        raise HTTPException(status_code=404, detail="Access not found")

    access, user, room = access_data
    return AccessResponse(
        id=access.id,
        user_id=access.user_id,
        user_name=user.name,
        room_id=access.room_id,
        room_name=room.name,
        from_hour=access.from_hour,
        to_hour=access.to_hour,
        all_time_access=access.all_time_access
    )


@router.get("/user/{user_id}", response_model=AccessResponse)
async def get_user_access(user_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Access, User, Room).join(User).join(Room).where(Access.user_id == user_id))
    access_data = result.first()
    if not access_data:
        raise HTTPException(status_code=404, detail="Access not found for this user")

    access, user, room = access_data
    return AccessResponse(
        id=access.id,
        user_id=access.user_id,
        user_name=user.name,
        room_id=access.room_id,
        room_name=room.name,
        from_hour=access.from_hour,
        to_hour=access.to_hour,
        all_time_access=access.all_time_access
    )


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

    # Get user and room details for response
    user_result = await db.execute(select(User).where(User.id == user_id))
    user = user_result.scalar_one()
    room_result = await db.execute(select(Room).where(Room.id == access.room_id))
    room = room_result.scalar_one()

    return AccessResponse(
        id=access.id,
        user_id=access.user_id,
        user_name=user.name,
        room_id=access.room_id,
        room_name=room.name,
        from_hour=access.from_hour,
        to_hour=access.to_hour,
        all_time_access=access.all_time_access
    )


@router.delete("/user/{user_id}")
async def delete_user_access(user_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Access).where(Access.user_id == user_id))
    access = result.scalar_one_or_none()
    if not access:
        raise HTTPException(status_code=404, detail="Access not found for this user")

    await db.delete(access)
    await db.commit()
    return {"message": "Access deleted successfully"}


@router.get("/check-access/{user_name}/{room_id}", response_model=CanAccessResponse)
async def check_can_access(user_name: str, room_id: int, db: AsyncSession = Depends(get_db)):
    # Get the room to check if it's locked
    room_result = await db.execute(select(Room).where(Room.id == room_id))
    room = room_result.scalar_one_or_none()

    if not room:
        return CanAccessResponse(
            can_access=False,
            message="Room not found"
        )

    # If room is locked, deny access completely
    if room.state == RoomState.LOCKED:
        return CanAccessResponse(
            can_access=False,
            message="Room is locked"
        )

    # Get user by name first
    user_result = await db.execute(select(User).where(User.name == user_name))
    user = user_result.scalar_one_or_none()

    if not user:
        return CanAccessResponse(
            can_access=False,
            message="User not found"
        )

    # Room is unlocked, now check user access permissions
    access_result = await db.execute(
        select(Access).where(
            and_(Access.user_id == user.id, Access.room_id == room_id)
        )
    )
    access = access_result.scalar_one_or_none()

    if not access:
        return CanAccessResponse(
            can_access=False,
            message="User does not have access to this room"
        )

    # If user has all_time_access, they can access when room is unlocked
    if access.all_time_access:
        return CanAccessResponse(
            can_access=True,
            message="User has all-time access to this room"
        )

    # Check time-based access
    if access.from_hour is None or access.to_hour is None:
        return CanAccessResponse(
            can_access=False,
            message="Access time configuration is invalid"
        )

    # Check current time
    current_time = datetime.now().time()

    # Handle time range that crosses midnight
    if access.from_hour <= access.to_hour:
        # Normal range (e.g., 9:00 to 17:00)
        can_access = access.from_hour <= current_time <= access.to_hour
    else:
        # Range crosses midnight (e.g., 22:00 to 06:00)
        can_access = current_time >= access.from_hour or current_time <= access.to_hour

    if can_access:
        return CanAccessResponse(
            can_access=True,
            message=f"User can access room from {access.from_hour} to {access.to_hour}"
        )
    else:
        return CanAccessResponse(
            can_access=False,
            message=f"Current time {current_time} is outside allowed access hours ({access.from_hour} to {access.to_hour})"
        )