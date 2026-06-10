from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker
from models import Base, User, Venue
from auth import hash_password

DATABASE_URL = "sqlite:///./quickslot.db"

# Connect timeout is set to 10 seconds to allow retry on lock wait.
engine = create_engine(
    DATABASE_URL, 
    connect_args={"check_same_thread": False, "timeout": 10}
)

# Set WAL mode and busy timeout for concurrent safety in SQLite
@event.listens_for(engine, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record):
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA journal_mode=WAL")
    cursor.execute("PRAGMA busy_timeout=5000")
    cursor.close()

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def init_db():
    Base.metadata.create_all(bind=engine)
    
    db = SessionLocal()
    try:
        # Seed users if they don't exist
        if db.query(User).count() == 0:
            default_pw = hash_password("password123")
            default_users = [
                User(id=1, name="Akash Patel", hashed_password=default_pw),
                User(id=2, name="Judge Alpha", hashed_password=default_pw),
                User(id=3, name="Judge Beta", hashed_password=default_pw),
                User(id=4, name="Test User 4", hashed_password=default_pw),
                User(id=5, name="Test User 5", hashed_password=default_pw),
            ]

            # TODO(security): Mock users for hackathon demonstration. 
            # In production, implement real user authentication & registration.
            db.add_all(default_users)
            db.commit()
            print("Seeded default users.")
            
        # Seed venues if they don't exist
        if db.query(Venue).count() == 0:
            default_venues = [
                Venue(id=1, name="Star Badminton Academy", location="Sector 62, Noida"),
                Venue(id=2, name="Elite Turf & Sports Arena", location="HSR Layout, Bengaluru"),
                Venue(id=3, name="Downtown Football Club", location="Andheri West, Mumbai"),
            ]
            db.add_all(default_venues)
            db.commit()
            print("Seeded default venues.")
    except Exception as e:
        print(f"Error initializing DB: {e}")
        db.rollback()
    finally:
        db.close()
