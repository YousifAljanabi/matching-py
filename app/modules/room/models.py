from sqlalchemy import Column, Integer, String, Enum
import enum
from app.core.database import Base


class RoomState(enum.Enum):
    LOCKED = "locked"
    UNLOCKED = "unlocked"


class Room(Base):
    __tablename__ = "rooms"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    state = Column(Enum(RoomState), nullable=False, default=RoomState.UNLOCKED)