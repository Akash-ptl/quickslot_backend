from fastapi import FastAPI, Depends, HTTPException, Header, status
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from typing import List, Optional
import datetime
from pydantic import BaseModel, Field

from database import get_db, init_db
from models import User, Venue, Booking
from auth import verify_password, create_access_token, get_current_user_id, hash_password

# Initialize DB on startup
init_db()

app = FastAPI(title="QuickSlot API", description="Concurrency-safe sports venue booking system")

# CORS Configuration
# TODO(security): Restrict CORS origins in production instead of allowing wildcard.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], 
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Helper to validate date format (YYYY-MM-DD)
def validate_date(date_str: str) -> bool:
    try:
        datetime.datetime.strptime(date_str, "%Y-%m-%d")
        return True
    except ValueError:
        return False

# Pydantic schemas
class UserResponse(BaseModel):
    id: int
    email: str
    name: str

    class Config:
        from_attributes = True

class VenueResponse(BaseModel):
    id: int
    name: str
    location: str

    class Config:
        from_attributes = True

class SlotResponse(BaseModel):
    slot_time: str # e.g. "06:00" for 6:00 AM - 7:00 AM
    status: str    # "available" or "booked"
    booking_id: Optional[int] = None
    booked_by_user_id: Optional[int] = None
    booked_by_user_name: Optional[str] = None

class BookingRequest(BaseModel):
    venue_id: int
    date: str = Field(pattern=r"^\d{4}-\d{2}-\d{2}$") # YYYY-MM-DD
    slot_time: str = Field(pattern=r"^\d{2}:00$")    # HH:00

class BookingResponse(BaseModel):
    id: int
    user_id: int
    venue_id: int
    venue_name: str
    venue_location: str
    date: str
    slot_time: str
    created_at: datetime.datetime

class LoginRequest(BaseModel):
    email: str = Field(pattern=r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$")
    password: str

class RegisterRequest(BaseModel):
    email: str = Field(pattern=r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$")
    name: str = Field(min_length=2)
    password: str = Field(min_length=6)

class LoginResponse(BaseModel):
    access_token: str
    token_type: str
    user: UserResponse

# Hourly slots from 6 AM to 10 PM (last slot starts at 9 PM: "21:00")
ALL_SLOTS = [f"{hour:02d}:00" for hour in range(6, 22)]

@app.get("/venues", response_model=List[VenueResponse])
def list_venues(db: Session = Depends(get_db)):
    return db.query(Venue).all()

@app.get("/users", response_model=List[UserResponse])
def list_users(db: Session = Depends(get_db)):
    return db.query(User).all()

@app.post("/auth/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def register(req: RegisterRequest, db: Session = Depends(get_db)):
    existing_user = db.query(User).filter(User.email == req.email).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered."
        )
    
    new_user = User(
        email=req.email,
        name=req.name,
        hashed_password=hash_password(req.password)
    )
    db.add(new_user)
    try:
        db.commit()
        db.refresh(new_user)
        return UserResponse.from_orm(new_user)
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to register user: {str(e)}"
        )

@app.post("/auth/login", response_model=LoginResponse)
def login(req: LoginRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == req.email).first()
    if not user or not verify_password(req.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password."
        )
    
    access_token = create_access_token(user.id)
    return LoginResponse(
        access_token=access_token,
        token_type="bearer",
        user=UserResponse.from_orm(user)
    )

@app.get("/venues/{venue_id}/slots", response_model=List[SlotResponse])
def get_slots(venue_id: int, date: str, db: Session = Depends(get_db)):
    if not validate_date(date):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, 
            detail="Invalid date format. Use YYYY-MM-DD."
        )
    
    # Check if venue exists
    venue = db.query(Venue).filter(Venue.id == venue_id).first()
    if not venue:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, 
            detail="Venue not found."
        )

    # Fetch all bookings for this venue and date
    bookings = db.query(Booking).filter(
        Booking.venue_id == venue_id,
        Booking.date == date
    ).all()
    
    # Map bookings by slot_time
    booking_map = {}
    for b in bookings:
        user = db.query(User).filter(User.id == b.user_id).first()
        booking_map[b.slot_time] = {
            "booking_id": b.id,
            "user_id": b.user_id,
            "user_name": user.name if user else "Unknown User"
        }

    # Generate output
    slots_status = []
    for slot_time in ALL_SLOTS:
        if slot_time in booking_map:
            slots_status.append(SlotResponse(
                slot_time=slot_time,
                status="booked",
                booking_id=booking_map[slot_time]["booking_id"],
                booked_by_user_id=booking_map[slot_time]["user_id"],
                booked_by_user_name=booking_map[slot_time]["user_name"]
            ))
        else:
            slots_status.append(SlotResponse(
                slot_time=slot_time,
                status="available"
            ))
            
    return slots_status

@app.post("/bookings", response_model=BookingResponse, status_code=status.HTTP_201_CREATED)
def create_booking(
    req: BookingRequest, 
    current_user_id: int = Depends(get_current_user_id), 
    db: Session = Depends(get_db)
):
    # Verify user exists
    user = db.query(User).filter(User.id == current_user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, 
            detail="Unauthorized User ID."
        )

    # Validate slot time range (6 AM to 9 PM start times)
    if req.slot_time not in ALL_SLOTS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, 
            detail="Invalid slot time. Slots must be between 06:00 and 21:00."
        )

    # Check if venue exists
    venue = db.query(Venue).filter(Venue.id == req.venue_id).first()
    if not venue:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, 
            detail="Venue not found."
        )

    # Create new booking
    new_booking = Booking(
        user_id=current_user_id,
        venue_id=req.venue_id,
        date=req.date,
        slot_time=req.slot_time
    )

    db.add(new_booking)
    try:
        db.commit()
        db.refresh(new_booking)
        return BookingResponse(
            id=new_booking.id,
            user_id=new_booking.user_id,
            venue_id=new_booking.venue_id,
            venue_name=venue.name,
            venue_location=venue.location,
            date=new_booking.date,
            slot_time=new_booking.slot_time,
            created_at=new_booking.created_at
        )
    except IntegrityError:
        db.rollback()
        # This occurs when unique constraint on (venue_id, date, slot_time) is violated
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Slot already booked by another user."
        )
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An unexpected database error occurred: {str(e)}"
        )

@app.get("/users/{user_id}/bookings", response_model=List[BookingResponse])
def get_user_bookings(
    user_id: int, 
    current_user_id: int = Depends(get_current_user_id), 
    db: Session = Depends(get_db)
):
    if current_user_id != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to view other users' bookings."
        )

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, 
            detail="User not found."
        )

    bookings = db.query(Booking).filter(Booking.user_id == user_id).all()
    
    response = []
    for b in bookings:
        venue = db.query(Venue).filter(Venue.id == b.venue_id).first()
        response.append(BookingResponse(
            id=b.id,
            user_id=b.user_id,
            venue_id=b.venue_id,
            venue_name=venue.name if venue else "Unknown Venue",
            venue_location=venue.location if venue else "Unknown Location",
            date=b.date,
            slot_time=b.slot_time,
            created_at=b.created_at
        ))
        
    return response

@app.delete("/bookings/{booking_id}", status_code=status.HTTP_200_OK)
def cancel_booking(
    booking_id: int, 
    current_user_id: int = Depends(get_current_user_id), 
    db: Session = Depends(get_db)
):
    booking = db.query(Booking).filter(Booking.id == booking_id).first()
    if not booking:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, 
            detail="Booking not found."
        )
    
    if booking.user_id != current_user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to cancel this booking."
        )
    
    try:
        db.delete(booking)
        db.commit()
        return {"detail": "Booking cancelled successfully."}
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to cancel booking: {str(e)}"
        )
