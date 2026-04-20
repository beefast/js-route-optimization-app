#!/usr/bin/env python3
"""
Call the Google Route Optimization API with a request JSON and save the response.

Authentication uses a gcloud access token. Obtain one with:
    gcloud auth print-access-token

Usage:
    PROJECT_ID=your-gcp-project-id
    TOKEN=$(gcloud auth print-access-token)

    # Quick sample test
    python run_api.py \\
        --request data/freshfull/request_sample.json \\
        --output  data/freshfull/response_sample.json \\
        --project $PROJECT_ID \\
        --token   $TOKEN

    # Full day
    python run_api.py \\
        --request data/freshfull/request_2026-03-23.json \\
        --output  data/freshfull/response_2026-03-23.json \\
        --project $PROJECT_ID \\
        --token   $TOKEN
"""

import argparse
import json
import socket
from http import client
from pathlib import Path

API_HOST = "routeoptimization.googleapis.com"
API_PATH = "/v1/projects/{project}:optimizeTours"


def optimize_tours(
    request: dict,
    project: str,
    token: str,
    timeout_s: int,
) -> dict:
    """POST request to the Route Optimization API and return the parsed response."""
    path = API_PATH.format(project=project)
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {token}",
        "x-goog-user-project": project,
        # Tells the server the maximum time to spend solving.
        "X-Server-Timeout": str(timeout_s),
    }

    conn = client.HTTPSConnection(API_HOST)
    conn.connect()

    # TCP keepalive — prevents connection drops on long solves (>1 min timeouts).
    sock = conn.sock
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_KEEPALIVE, 1)
    sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_KEEPIDLE, 60)
    sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_KEEPINTVL, 60)
    sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_KEEPCNT, max(timeout_s // 30, 1))

    body = json.dumps(request)
    conn.request("POST", path, body=body, headers=headers)
    response = conn.getresponse()

    if response.status != 200:
        raw = response.read().decode("utf-8", errors="replace")
        raise RuntimeError(
            f"API returned {response.status} {response.reason}:\n{raw}"
        )

    return json.load(response)


def _summarize(response: dict, request: dict) -> None:
    """Print a quick human-readable summary of the optimization result."""
    routes   = response.get("routes", [])
    skipped  = response.get("skippedShipments", [])
    vehicles = request["model"]["vehicles"]
    n_orders = len(request["model"]["shipments"])

    served = n_orders - len(skipped)
    print(f"\n{'─' * 50}")
    print(f"  Orders total:    {n_orders}")
    print(f"  Orders served:   {served}  ({100 * served / max(n_orders, 1):.1f}%)")
    print(f"  Skipped:         {len(skipped)}")
    print(f"  Routes used:     {len(routes)} / {len(vehicles)} vehicles")

    total_km = 0.0
    total_visits = 0
    for r in routes:
        metrics = r.get("metrics", {})
        total_km     += metrics.get("travelDistanceMeters", 0) / 1000
        total_visits += metrics.get("performedShipmentCount", 0)

    if routes:
        print(f"  Total km:        {total_km:.1f} km")
        print(f"  Avg km/order:    {total_km / max(total_visits, 1):.2f} km")
        print(f"  Avg orders/route:{total_visits / len(routes):.1f}")
    print(f"{'─' * 50}\n")

    if skipped:
        reasons = {}
        for s in skipped:
            for reason in s.get("reasons", []):
                code = reason.get("code", "UNKNOWN")
                reasons[code] = reasons.get(code, 0) + 1
        print("  Skip reasons:")
        for code, count in sorted(reasons.items(), key=lambda x: -x[1]):
            print(f"    {code}: {count}")
        print()


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Call the Route Optimization API and save the response."
    )
    parser.add_argument("--request", required=True, help="Path to request JSON file (from transform.py)")
    parser.add_argument("--output",  required=True, help="Path to write response JSON")
    parser.add_argument("--project", required=True, help="GCP project ID")
    parser.add_argument("--token",   required=True, help="gcloud access token (gcloud auth print-access-token)")
    args = parser.parse_args()

    request_path = Path(args.request)
    output_path  = Path(args.output)

    request = json.loads(request_path.read_text())
    timeout_s = int(request.get("timeout", "60s").rstrip("s"))

    n_s = len(request["model"]["shipments"])
    n_v = len(request["model"]["vehicles"])
    label = request.get("label", "?")
    print(f"[run_api] Scenario: {label}")
    print(f"[run_api] {n_s} shipments, {n_v} vehicles, timeout={timeout_s}s")
    print(f"[run_api] Calling {API_HOST}...")

    response = optimize_tours(request, args.project, args.token, timeout_s)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(response, indent=2, ensure_ascii=False))
    print(f"[run_api] Response saved to {output_path}")

    _summarize(response, request)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
