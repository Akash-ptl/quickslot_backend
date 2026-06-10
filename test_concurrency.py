import urllib.request
import urllib.error
import json
import concurrent.futures
import time

URL = "http://127.0.0.1:8000/bookings"
payload = {
    "venue_id": 1,
    "date": "2026-06-12",
    "slot_time": "09:00"
}
data = json.dumps(payload).encode("utf-8")

def book_slot(user_id):
    req = urllib.request.Request(
        URL, 
        data=data, 
        headers={
            "X-User-Id": str(user_id),
            "Content-Type": "application/json"
        },
        method="POST"
    )
    try:
        # Measure time of sending
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
    print("Starting concurrency test...")
    print(f"Sending 5 parallel booking requests for the same slot (Venue 1, Date: 2026-06-12, Time: 09:00)...")

    # Use ThreadPoolExecutor to trigger requests at the same time
    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
        # Submit requests
        futures = {executor.submit(book_slot, user_id): user_id for user_id in range(1, 6)}
        
        results = []
        for future in concurrent.futures.as_completed(futures):
            user_id = futures[future]
            try:
                status, body, req_time = future.result()
                results.append((user_id, status, body, req_time))
            except Exception as e:
                print(f"User {user_id} failed with error: {e}")

    # Sort results by response arrival/completion
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
