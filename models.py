from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, UniqueConstraint
from sqlalchemy.orm import declarative_base
import datetime

Base = declarative_base()

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    name = Column(String, nullable=False)
    hashed_password = Column(String, nullable=False)

class Venue(Base):
    __tablename__ = "venues"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    location = Column(String, nullable=False)

class Booking(Base):
    __tablename__ = "bookings"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    venue_id = Column(Integer, ForeignKey("venues.id"), nullable=False)
    # date in YYYY-MM-DD format
    date = Column(String, nullable=False, index=True)
    # slot_time in HH:MM format (e.g. "06:00")
    slot_time = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    # CRITICAL: Unique constraint to prevent double-booking at the DB level!
    __table_args__ = (
        UniqueConstraint("venue_id", "date", "slot_time", name="uix_venue_date_slot"),
    )
