import urllib.request
import urllib.error
import json
import concurrent.futures
import time

URL = "http://127.0.0.1:8000/bookings"
payload = {
    "venue_id": 1,
    "date": "2026-06-12",
    "slot_time": "11:00"  # Changed to 11:00 to avoid conflicts with previous tests
}
data = json.dumps(payload).encode("utf-8")

# In-memory storage for user tokens
user_tokens = {}

def register_user(i):
    url = "http://127.0.0.1:8000/auth/register"
    payload = json.dumps({
        "email": f"testuser{i}@example.com",
        "name": f"Test User {i}",
        "password": "password123"
    }).encode("utf-8")
    
    req = urllib.request.Request(
        url,
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST"
    )
    try:
        with urllib.request.urlopen(req) as response:
            return response.status
    except urllib.error.HTTPError as e:
        # 400 Bad Request indicates email already registered, which is fine
        if e.code == 400:
            return 200
        return e.code
    except Exception:
        return 500

def get_token(i):
    login_url = "http://127.0.0.1:8000/auth/login"
    login_payload = json.dumps({
        "email": f"testuser{i}@example.com",
        "password": "password123"
    }).encode("utf-8")
    
    req = urllib.request.Request(
        login_url,
        data=login_payload,
        headers={"Content-Type": "application/json"},
        method="POST"
    )
    try:
        with urllib.request.urlopen(req) as response:
            resp_body = json.loads(response.read().decode("utf-8"))
            return resp_body["access_token"]
    except Exception as e:
        print(f"Failed to login user {i}: {e}")
        return None

def book_slot(user_id):
    token = user_tokens.get(user_id)
    req = urllib.request.Request(
        URL, 
        data=data, 
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        },
        method="POST"
    )
    try:
        start_time = time.time()
        with urllib.request.urlopen(req) as response:
            resp_body = response.read().decode("utf-8")
            return response.status, resp_body, start_time
    except urllib.error.HTTPError as e:
        resp_body = e.read().decode("utf-8")
        return e.code, resp_body, start_time
    except Exception as e:
        return 500, str(e), time.time()

def main():
    print("Starting concurrency test (Email & Password flow)...")
    
    print("Programmatically registering 5 separate test users...")
    for i in range(1, 6):
        register_user(i)
        
    print("Pre-fetching auth tokens for test users (1 to 5)...")
    for i in range(1, 6):
        token = get_token(i)
        if token:
            user_tokens[i] = token
        else:
            print("Failed to get tokens for all test users. Aborting test.")
            return

    print(f"Sending 5 parallel booking requests for the same slot (Venue 1, Date: 2026-06-12, Time: 11:00)...")

    # Use ThreadPoolExecutor to trigger requests at the same time
    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
        futures = {executor.submit(book_slot, user_id): user_id for user_id in range(1, 6)}
        
        results = []
        for future in concurrent.futures.as_completed(futures):
            user_id = futures[future]
            try:
                status, body, req_time = future.result()
                results.append((user_id, status, body, req_time))
            except Exception as e:
                print(f"User {user_id} failed with error: {e}")

    # Sort results
    print("\n--- RESULTS ---")
    success_count = 0
    conflict_count = 0
    other_count = 0

    for user_id, status, body, req_time in results:
        print(f"User {user_id} -> HTTP Status: {status} | Body: {body}")
        if status == 201:
            success_count += 1
        elif status == 409:
            conflict_count += 1
        else:
            other_count += 1

    print("\n--- SUMMARY ---")
    print(f"Successes (201): {success_count} (Expected: 1)")
    print(f"Conflicts (409): {conflict_count} (Expected: 4)")
    if other_count > 0:
        print(f"Other Errors: {other_count}")
        
    if success_count == 1 and conflict_count == 4:
        print("\nSUCCESS: Concurrency protection verified! Only one request succeeded, others were rejected.")
    else:
        print("\nFAILURE: Check configuration or timing issues.")

if __name__ == "__main__":
    main()
