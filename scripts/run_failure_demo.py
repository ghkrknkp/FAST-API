"""
Automated Failure Simulation & Alert Demonstration Script.
Executes controlled traffic bursts to test:
  1. Scenario 1: Authentication failure (HTTP 401) on /protected
  2. Scenario 2: Slow API latency / timeout (> 3s SLA breach) on /simulate-timeout
  3. Scenario 3: Internal server error (HTTP 500) on /simulate-error
  4. Scenario 4: Rate limit quota exceeded (HTTP 429) on /simulate-rate-limit
  5. Healthy baseline traffic on /, /health, /users, /products
"""

import sys
import time
import requests

BASE_URL = "http://localhost:8000"


def log(msg: str):
    print(f"[{time.strftime('%H:%M:%S')}] {msg}")


def check_api_online():
    log(f"Checking if API is reachable at {BASE_URL}...")
    try:
        res = requests.get(f"{BASE_URL}/health", timeout=3)
        if res.status_code == 200:
            log("API is ONLINE and HEALTHY.")
            return True
    except Exception as e:
        log(f"API is not responding yet: {e}")
    return False


def run_baseline_traffic(count: int = 15):
    log(f"--- Sending {count} baseline healthy requests (/, /health, /users, /products) ---")
    endpoints = ["/", "/health", "/users", "/products"]
    for i in range(count):
        ep = endpoints[i % len(endpoints)]
        try:
            r = requests.get(f"{BASE_URL}{ep}", timeout=2)
            log(f"  GET {ep} -> {r.status_code}")
        except Exception as e:
            log(f"  GET {ep} failed: {e}")
        time.sleep(0.1)


def run_scenario_1_auth_failure():
    log("\n========================================================")
    log("SCENARIO 1: Invalid / Missing API Authentication (HTTP 401)")
    log("========================================================")
    log("Action 1: Calling /protected without X-API-Key header...")
    r1 = requests.get(f"{BASE_URL}/protected")
    log(f"  Result: {r1.status_code} {r1.json()}")

    log("Action 2: Calling /protected with bogus API key...")
    r2 = requests.get(f"{BASE_URL}/protected", headers={"X-API-Key": "invalid-token-123"})
    log(f"  Result: {r2.status_code} {r2.json()}")

    log("Action 3: Calling /protected with VALID API key...")
    r3 = requests.get(f"{BASE_URL}/protected", headers={"X-API-Key": "secret-token-demo-key-12345"})
    log(f"  Result: {r3.status_code} {r3.json()}")

    log("Action 4: Generating controlled burst of 401s to trigger AuthenticationFailureSpike alert...")
    for _ in range(5):
        requests.get(f"{BASE_URL}/protected")
        time.sleep(0.1)
    log("Scenario 1 execution complete.")


def run_scenario_2_timeout():
    log("\n========================================================")
    log("SCENARIO 2: Slow Response / Timeout Simulation (> 3s SLA)")
    log("========================================================")
    log("Action 1: Calling /simulate-timeout?delay=3.5s (triggers SlowAPIResponse alert)...")
    start = time.time()
    try:
        r = requests.get(f"{BASE_URL}/simulate-timeout?delay=3.5", timeout=5.0)
        elapsed = time.time() - start
        log(f"  Result: {r.status_code} in {elapsed:.2f}s -> {r.json()}")
    except requests.exceptions.Timeout:
        log("  Result: Client-side timeout observed as expected.")

    log("Action 2: Demonstrating client timeout cancellation with timeout=1.0s...")
    try:
        requests.get(f"{BASE_URL}/simulate-timeout?delay=3.5", timeout=1.0)
    except requests.exceptions.Timeout:
        log("  Result: Client aborted request after 1.0s while server handled safely.")
    log("Scenario 2 execution complete.")


def run_scenario_3_server_error():
    log("\n========================================================")
    log("SCENARIO 3: Internal Server Error (HTTP 500)")
    log("========================================================")
    log("Action 1: Triggering deliberate HTTP 500 on /simulate-error...")
    for _ in range(5):
        r = requests.get(f"{BASE_URL}/simulate-error")
        log(f"  Result: {r.status_code} -> {r.json()}")
        time.sleep(0.1)
    log("Scenario 3 execution complete.")


def run_scenario_4_rate_limit():
    log("\n========================================================")
    log("SCENARIO 4: Rate Limit Exceeded (HTTP 429)")
    log("========================================================")
    log("Action 1: Calling /simulate-rate-limit...")
    for _ in range(5):
        r = requests.get(f"{BASE_URL}/simulate-rate-limit")
        retry_after = r.headers.get("Retry-After", "N/A")
        log(f"  Result: {r.status_code} (Retry-After: {retry_after}s) -> {r.json()}")
        time.sleep(0.1)
    log("Scenario 4 execution complete.")


def verify_metrics_recorded():
    log("\n========================================================")
    log("Verifying Metrics at /metrics")
    log("========================================================")
    r = requests.get(f"{BASE_URL}/metrics")
    if r.status_code == 200:
        lines = [line for line in r.text.split("\n") if line.startswith("fastapi_") and not line.startswith("fastapi_request_duration_seconds_bucket")]
        log(f"Found {len(lines)} active metric points. Sample:")
        for line in lines[:10]:
            log(f"  {line}")


def main():
    if not check_api_online():
        log("Error: FastAPI is not running. Please start the app or run 'docker compose up -d' first.")
        sys.exit(1)

    run_baseline_traffic(12)
    run_scenario_1_auth_failure()
    run_scenario_2_timeout()
    run_scenario_3_server_error()
    run_scenario_4_rate_limit()
    run_baseline_traffic(8)
    verify_metrics_recorded()
    log("\n[SUCCESS] All 4 failure scenarios demonstrated and metrics populated!")


if __name__ == "__main__":
    main()
