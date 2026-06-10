# QuickSlot Backend

A lightweight, concurrency-safe REST API for booking sports venue slots (turf grounds, badminton courts). Built with Python 3.11+, FastAPI, and SQLAlchemy, using SQLite as the database engine.

---

## Technical Stack & Design Choices

* **Framework**: FastAPI (async event loop, automatic Swagger/OpenAPI docs generation).
* **Database**: SQLite (local file persistence). 
* **Database Concurrency Protection**: 
  We enforce the "no double-booking" rule at the database transaction layer using a composite Unique Index on the `bookings` table:
  ```sql
  UNIQUE(venue_id, date, slot_time)
  ```
  SQLite is configured in **WAL (Write-Ahead Logging)** mode with a **busy timeout of 5000ms**. If two threads try to write a booking for the same slot simultaneously, the database engine processes one write and blocks/rejects the second one with an `IntegrityError`. The API captures this exception and returns an HTTP `409 Conflict` status.
* **Authentication**: Simplified header-based auth (`X-User-Id` header) to avoid auth overhead, as permitted by the hackathon requirements.

---

## API Endpoints & Core User Flow

```text
  [User Client] ──(1. Get Venues)──► GET /venues 
  [User Client] ──(2. Check Slots)─► GET /venues/{id}/slots?date=YYYY-MM-DD
  [User Client] ──(3. Book Slot)───► POST /bookings (Header: X-User-Id)
  [User Client] ──(4. My Bookings)─► GET /users/{id}/bookings
  [User Client] ──(5. Cancel Slot)─► DELETE /bookings/{id}
```

### 1. Venue List
* **Endpoint**: `GET /venues`
* **Flow**: Client fetches seeded venues to display in the main dashboard.

### 2. Slot Status Verification
* **Endpoint**: `GET /venues/{id}/slots?date=YYYY-MM-DD`
* **Flow**: Returns 16 hourly slots (from `06:00` to `21:00`). Cross-references database records to set slot status (`available` or `booked`) along with who booked it.

### 3. Concurrency-Safe Booking
* **Endpoint**: `POST /bookings`
* **Payload**: `{"venue_id": int, "date": "YYYY-MM-DD", "slot_time": "HH:00"}`
* **Headers**: `X-User-Id: <user_id>`
* **Responses**:
  * `201 Created`: Booking successful.
  * `409 Conflict`: Slot already booked by another user.
  * `400 Bad Request`: Invalid input format (dates/slot hours).
  * `401 Unauthorized`: Invalid/Missing `X-User-Id`.

### 4. Active Booking History
* **Endpoint**: `GET /users/{user_id}/bookings`
* **Flow**: Returns all bookings associated with the specified user profile, enriched with venue names and location details.

### 5. Booking Cancellation
* **Endpoint**: `DELETE /bookings/{booking_id}`
* **Flow**: Deletes the booking row, instantly making the slot available again for other users.

---

## Running the API Locally

### 1. Installation
Ensure Python 3.11 is installed, then set up the virtual environment:
```bash
# Setup venv
python3.11 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### 2. Startup
Start the local hot-reloading server:
```bash
uvicorn main:app --reload --host 127.0.0.1 --port 8000
```
On startup, the app automatically initializes `quickslot.db` and seeds 3 sports venues and 5 default testing users.

---

## Concurrency Testing

To simulate simultaneous bookings under high load, run the provided automated script:
```bash
python test_concurrency.py
```
This spawns **5 threads** firing parallel POST requests to the same slot at the exact same millisecond. Output will demonstrate that exactly **1 request succeeds** (`201`) and the other **4 fail** (`409 Conflict`).
