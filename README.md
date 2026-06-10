# QuickSlot Backend REST API 🌐

A secure and concurrency-safe REST API for booking sports venue slots, built with Python 3.11, FastAPI, and SQLAlchemy ORM.

---

## 🔗 Live Production Endpoint
* **Base URL**: [https://quickslot-backend-jdhl.onrender.com](https://quickslot-backend-jdhl.onrender.com)
* **API Documentation**: [https://quickslot-backend-jdhl.onrender.com/docs](https://quickslot-backend-jdhl.onrender.com/docs) (Swagger UI)

---

## 📐 Concurrency Safety & Technical Stack
* **Framework**: FastAPI (async event loop, automatic Swagger generation).
* **Database**: SQLite (WAL mode enabled with a `5000ms` busy timeout for stable concurrent writes).
* **Database Concurrency Protection**: Double-booking collisions are handled cleanly at the database layer via a unique composite index constraint on `bookings(venue_id, date, slot_time)`. Simultaneous writes target the same slot yield exactly one success (`201`) and one failure (`409 Conflict`).
* **Authentication**: Password encryption using `bcrypt` and token verification via **OAuth2 JWT Access Tokens**.

---

## 🔄 API Endpoints
* `POST /auth/register` - Create user accounts.
* `POST /auth/login` - Validate credentials and return JWT bearer tokens.
* `GET /venues` - Retrieve sports venue listings.
* `GET /venues/{id}/slots?date=YYYY-MM-DD` - Retrieve slots for a date with status.
* `POST /bookings` - Reserve a slot (Header: `Authorization: Bearer <JWT>`).
* `GET /users/{id}/bookings` - View active bookings (Header: `Authorization: Bearer <JWT>`).
* `DELETE /bookings/{id}` - Cancel an active booking (Header: `Authorization: Bearer <JWT>`).

---

## 🚀 Running Locally & Testing Concurrency

### 1. Run Server
```bash
# Setup environment
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Start local server
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

### 2. Run Concurrency Test
```bash
python test_concurrency.py
```
*Spawns 5 concurrent threads executing reservation calls to the same slot at the exact same millisecond. Output will demonstrate exactly 1 success (`201`) and 4 errors (`409 Conflict`).*
