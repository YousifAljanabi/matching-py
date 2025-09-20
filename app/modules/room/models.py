from sqlalchemy import Column, Integer, String, ForeignKey, Enum
from sqlalchemy.orm import relationship
import enum
from app.core.database import Base


class RoomState(enum.Enum):
    LOCKED = "locked"
    UNLOCKED = "unlocked"


class Room(Base):
    __tablename__ = "rooms"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    owner_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    state = Column(Enum(RoomState), nullable=False, default=RoomState.UNLOCKED)

    owner = relationship("User", back_populates="owned_rooms")