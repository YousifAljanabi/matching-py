from sqlalchemy import Column, Integer, ForeignKey, Time, Boolean
from sqlalchemy.orm import relationship
from app.core.database import Base


class Access(Base):
    __tablename__ = "access"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    room_id = Column(Integer, ForeignKey("rooms.id"), nullable=False)
    from_hour = Column(Time, nullable=True)
    to_hour = Column(Time, nullable=True)
    all_time_access = Column(Boolean, nullable=False, default=False)

    user = relationship("User")
    room = relationship("Room")