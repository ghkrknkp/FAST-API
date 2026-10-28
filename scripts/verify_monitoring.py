"""
Monitoring Stack Verification Utility.
Checks container reachability, verifies Prometheus target health,
and checks Prometheus alerting rules status.
"""

import sys
import requests

SERVICES = {
    "FastAPI Application": "http://localhost:8000/health",
    "FastAPI Metrics Endpoint": "http://localhost:8000/metrics",
    "Prometheus Web UI": "http://localhost:9090/-/healthy",
    "Alertmanager Web UI": "http://localhost:9093/-/healthy",
    "Grafana Web UI": "http://localhost:3000/api/health",
}


def check_services():
    print("=" * 60)
    print("1. CHECKING SERVICE HEALTH")
    print("=" * 60)
    all_ok = True
    for name, url in SERVICES.items():
        try:
            r = requests.get(url, timeout=3)
            status = "OK" if r.status_code in [200, 302] else f"HTTP {r.status_code}"
            print(f"  [+] {name:30} : {status}")
        except Exception as e:
            print(f"  [-] {name:30} : FAILED ({e})")
            all_ok = False
    return all_ok


def check_prometheus_targets():
    print("\n" + "=" * 60)
    print("2. CHECKING PROMETHEUS SCRAPE TARGETS")
    print("=" * 60)
    try:
        r = requests.get("http://localhost:9090/api/v1/targets", timeout=3)
        if r.status_code == 200:
            data = r.json().get("data", {})
            active_targets = data.get("activeTargets", [])
            for target in active_targets:
                job = target.get("labels", {}).get("job")
                health = target.get("health")
                url = target.get("scrapeUrl")
                last_scrape = target.get("lastScrape")
                print(f"  Target [{job:10}] -> Health: {health:5} | Scrape URL: {url} (Last: {last_scrape})")
        else:
            print(f"  Failed to query targets: HTTP {r.status_code}")
    except Exception as e:
        print(f"  Error querying Prometheus targets: {e}")


def check_prometheus_alerts():
    print("\n" + "=" * 60)
    print("3. CHECKING PROMETHEUS ALERT RULES")
    print("=" * 60)
    try:
        r = requests.get("http://localhost:9090/api/v1/rules", timeout=3)
        if r.status_code == 200:
            groups = r.json().get("data", {}).get("groups", [])
            for g in groups:
                print(f"  Rule Group: {g.get('name')}")
                for rule in g.get("rules", []):
                    alert_name = rule.get("name")
                    state = rule.get("state")
                    health = rule.get("health")
                    print(f"    - {alert_name:28} | State: {state:8} | Rule Health: {health}")
        else:
            print(f"  Failed to query rules: HTTP {r.status_code}")
    except Exception as e:
        print(f"  Error querying Prometheus rules: {e}")


if __name__ == "__main__":
    check_services()
    check_prometheus_targets()
    check_prometheus_alerts()
