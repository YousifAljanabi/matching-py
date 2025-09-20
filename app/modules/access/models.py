from sqlalchemy import Column, Integer, ForeignKey, Time
from sqlalchemy.orm import relationship
from app.core.database import Base


class Access(Base):
    __tablename__ = "access"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    room_id = Column(Integer, ForeignKey("rooms.id"), nullable=False)
    from_hour = Column(Time, nullable=False)
    to_hour = Column(Time, nullable=False)

    user = relationship("User")
    room = relationship("Room")