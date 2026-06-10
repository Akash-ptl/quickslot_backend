# QuickSlot Backend REST API

A highly professional, secure, and concurrency-safe REST API for booking sports venue slots (turf grounds, badminton courts). Built with Python 3.11, FastAPI, and SQLAlchemy ORM, using a tuned SQLite engine as the persistent database store.

---

## 🔗 Live Production Endpoint
The API is deployed and running live on Render:
* **Base URL**: [https://quickslot-backend-jdhl.onrender.com](https://quickslot-backend-jdhl.onrender.com)
* **API Documentation**: [https://quickslot-backend-jdhl.onrender.com/docs](https://quickslot-backend-jdhl.onrender.com/docs) (Swagger UI)

---

## 🛠️ Technical Stack & Design Choices

* **Framework**: FastAPI (async event loop, automatic OpenAPI/Swagger schema generation).
* **Database**: SQLite (WAL mode enabled with a `5000ms` busy timeout for stable concurrent writes).
* **Database Concurrency Protection**: 
  Double-booking collisions are handled cleanly at the database transaction layer via a composite Unique Index on the `bookings` table:
  ```sql
  UNIQUE(venue_id, date, slot_time)
  ```
  If two threads try to write a booking for the exact same slot simultaneously, the database engine processes one write and blocks/rejects the second one with an `IntegrityError`. The API captures this exception and returns an HTTP `409 Conflict` status.
* **Security & Authentication**:
  * Passwords are encrypted in the database using `bcrypt` hashing.
  * Token-based authentication using **OAuth2 Bearer JWT Access Tokens**.
  * User credentials validation yields a secure token (expired after 60 minutes) which is required for all state-changing endpoints (`POST /bookings`, `GET /users/{id}/bookings`, `DELETE /bookings/{id}`).

---

## 🔄 Core User Flow & Endpoints

```text
  [User Client] ──(1. Register / Login)─► POST /auth/register & POST /auth/login
  [User Client] ──(2. Get Venues)───────► GET /venues
  [User Client] ──(3. Check Slots)──────► GET /venues/{id}/slots?date=YYYY-MM-DD
  [User Client] ──(4. Book Slot)────────► POST /bookings (Header: Authorization: Bearer <JWT>)
  [User Client] ──(5. View Bookings)────► GET /users/{id}/bookings (Header: Authorization: Bearer <JWT>)
  [User Client] ──(6. Cancel Booking)───► DELETE /bookings/{id} (Header: Authorization: Bearer <JWT>)
```

### 1. Authentication Endpoints
* **`POST /auth/register`**: Creates a new user account with hashed password.
  * *Request Body*: `{"email": "user@example.com", "name": "User Name", "password": "secure_password"}`
* **`POST /auth/login`**: Validates credentials and returns JWT bearer token.
  * *Request Body*: `{"email": "user@example.com", "password": "secure_password"}`
  * *Response*: `{"access_token": "eyJhbG...", "token_type": "bearer", "user": {"id": 1, "email": "...", "name": "..."}}`

### 2. Dashboard Endpoints
* **`GET /venues`**: Retrieves all sports venues in the network.
* **`GET /venues/{id}/slots?date=YYYY-MM-DD`**: Lists all 16 slots (`06:00` to `21:00`) for a selected date. Shows `available` / `booked` status, booking IDs, and the name of the user who reserved it.

### 3. Booking Transactions (Secured)
* **`POST /bookings`**: Reserves a slot.
  * *Headers*: `Authorization: Bearer <JWT_Token>`
  * *Body*: `{"venue_id": int, "date": "YYYY-MM-DD", "slot_time": "HH:00"}`
  * *Responses*:
    * `201 Created`: Booking successful.
    * `409 Conflict`: Slot already booked by another user.
    * `401 Unauthorized`: Invalid/missing token.
* **`GET /users/{id}/bookings`**: Retrieves active bookings for the specified user.
* **`DELETE /bookings/{id}`**: Cancels an active booking, freeing up the slot instantly.

---

## ⚡ Concurrency Testing

To simulate simultaneous bookings under high load, run the provided automated script:
```bash
# Setup virtual environment
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Run concurrent bookings simulation
python test_concurrency.py
```
This script pre-registers 5 users, gets their JWT access tokens, and fires **5 parallel threads** executing booking requests targeting the exact same slot at the exact same millisecond. Output will demonstrate that exactly **1 request succeeds** (`201`) and the other **4 fail** (`409 Conflict`).

---

## 🚀 Deployment & Local Setup
* **Production Deployed API**: [https://quickslot-backend-jdhl.onrender.com](https://quickslot-backend-jdhl.onrender.com)
* **Interactive OpenAPI/Swagger Docs**: [https://quickslot-backend-jdhl.onrender.com/docs](https://quickslot-backend-jdhl.onrender.com/docs)

To spin up the server locally:
```bash
uvicorn main:app --reload --host 127.0.0.1 --port 8000
```
*Note: On launch, the server automatically initializes `quickslot.db` and seeds database tables with sports venues, courts, and a default testing account (`akash@example.com` / `password123`).*
