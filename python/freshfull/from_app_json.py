#!/usr/bin/env python3
"""
Convert the optimized scenario downloaded from the Fleet Routing app into the
Freshfull output format (Rezultate simulare.xlsx).

The app exports a ZIP file containing:
  scenario.json  — the OptimizeToursRequest (shipments, vehicles, model)
  solution.json  — the OptimizeToursResponse (routes, visits, metrics)

Output columns (matches Rezultate simulare.xlsx):
  DataStartLivrare, DataEndLivrare, Comanda, DataPlasareComanda,
  Sofer, IntervalClient, DataLivrareSolicitataClient,
  TipVehicul, TipProgramSofer, Cursa, DataStartCursa, DataEndCursa

Usage:
    # From the downloaded ZIP
    python -m python.freshfull.from_app_json \\
        --zip  gmpro_20260323120000.zip \\
        --output data/freshfull/rezultate_2026-03-23.xlsx

    # Or from extracted JSON files
    python -m python.freshfull.from_app_json \\
        --scenario data/freshfull/scenario.json \\
        --solution data/freshfull/solution.json \\
        --output   data/freshfull/rezultate_2026-03-23.xlsx
"""

import argparse
import json
import zipfile
from datetime import datetime, timedelta, timezone
from pathlib import Path

import openpyxl
from openpyxl.styles import Alignment, Font, PatternFill

UTC_OFFSET_HOURS = 2      # Romania EET; match value used in to_app_csvs.py
DELIVERY_DURATION_MIN = 7

HEADERS = [
    "DataStartLivrare",
    "DataEndLivrare",
    "Comanda",
    "DataPlasareComanda",
    "Sofer",
    "IntervalClient",
    "DataLivrareSolicitataClient",
    "TipVehicul",
    "TipProgramSofer",
    "Cursa",
    "DataStartCursa",
    "DataEndCursa",
]

_LOCAL_TZ = timezone(timedelta(hours=UTC_OFFSET_HOURS))
_HEADER_FILL = PatternFill("solid", fgColor="D9E1F2")
_HEADER_FONT = Font(bold=True, name="Calibri")
_BODY_FONT   = Font(name="Calibri")
_CENTER      = Alignment(horizontal="center", vertical="center")
_LEFT        = Alignment(horizontal="left",   vertical="center")


# ── Timestamp parsing ────────────────────────────────────────────────────────

def parse_ts(value) -> datetime | None:
    """
    Parse a timestamp from the app's JSON export.
    Handles:
      - RFC 3339 strings: "2026-03-23T04:00:00Z"  (canonical=true export)
      - Proto object:     {"seconds": "1742702400"} (fallback)
    """
    if not value:
        return None
    if isinstance(value, str):
        s = value.replace("Z", "+00:00")
        return datetime.fromisoformat(s).astimezone(timezone.utc)
    if isinstance(value, dict):
        secs = int(value.get("seconds", 0))
        nanos = int(value.get("nanos", 0))
        return datetime.fromtimestamp(secs + nanos / 1e9, tz=timezone.utc)
    return None


def to_local(dt: datetime | None) -> datetime | None:
    return dt.astimezone(_LOCAL_TZ) if dt else None


def fmt(dt: datetime | None) -> str:
    return dt.strftime("%Y-%m-%d %H:%M") if dt else ""


# ── Vehicle metadata helpers ─────────────────────────────────────────────────

def vehicle_type(label: str) -> str:
    prefix = label.split("-")[0].upper() if label else ""
    return {"IV": "Iveco", "PG": "Peugeot", "RN": "Renault"}.get(prefix, label)


def shift_type(vehicle: dict) -> str:
    """
    Read the shift type from the vehicle's end time window span.
    Approximates: end_window_end - start_window_start ≈ shift hours.
    Falls back to '10h'.
    """
    try:
        t_start = parse_ts(
            (vehicle.get("startTimeWindows") or [{}])[0].get("startTime")
        )
        t_end = parse_ts(
            (vehicle.get("endTimeWindows") or [{}])[0].get("endTime")
        )
        if t_start and t_end:
            span_h = (t_end - t_start).total_seconds() / 3600
            if span_h <= 9:
                return "8h"
            if span_h <= 11:
                return "10h"
            return "12h"
    except (KeyError, IndexError, TypeError):
        pass
    return "10h"


# ── Core conversion ──────────────────────────────────────────────────────────

def build_rows(scenario: dict, solution: dict) -> list[dict]:
    """Join solution routes/visits with scenario shipment metadata."""
    shipments = scenario.get("model", scenario).get("shipments", [])
    vehicles  = scenario.get("model", scenario).get("vehicles", [])
    rows = []

    for route_idx, route in enumerate(solution.get("routes", [])):
        v_idx   = route.get("vehicleIndex", 0)
        vehicle = vehicles[v_idx] if v_idx < len(vehicles) else {}
        v_label = route.get("vehicleLabel") or vehicle.get("label") or f"V-{v_idx:03d}"
        v_type  = vehicle_type(v_label)
        shift   = shift_type(vehicle)

        route_start = to_local(parse_ts(route.get("vehicleStartTime")))
        route_end   = to_local(parse_ts(route.get("vehicleEndTime")))
        cursa_id    = (
            f"{v_label}-" + route_start.strftime("%m%d-%H%M")
            if route_start else f"CURSA-{route_idx:04d}"
        )

        for visit in route.get("visits", []):
            # Skip pickup visits (Freshfull orders are delivery-only, but be safe)
            if visit.get("isPickup"):
                continue

            s_idx    = visit.get("shipmentIndex", 0)
            shipment = shipments[s_idx] if s_idx < len(shipments) else {}
            order_id = visit.get("shipmentLabel") or shipment.get("label") or str(s_idx)

            visit_start = to_local(parse_ts(visit.get("startTime")))
            visit_end   = (
                visit_start + timedelta(minutes=DELIVERY_DURATION_MIN)
                if visit_start else None
            )

            # Customer time window from the scenario's delivery time windows
            deliveries = shipment.get("deliveries", [])
            tw_start_local = tw_end_local = None
            if deliveries:
                tw_list = deliveries[0].get("timeWindows") or [{}]
                tw = tw_list[0]
                tw_start_local = to_local(parse_ts(tw.get("startTime")))
                tw_end_local   = to_local(parse_ts(tw.get("endTime")))

            interval_str = (
                f"{tw_start_local.strftime('%H:%M')} - {tw_end_local.strftime('%H:%M')}"
                if tw_start_local and tw_end_local else ""
            )

            rows.append({
                "DataStartLivrare":            fmt(visit_start),
                "DataEndLivrare":              fmt(visit_end),
                "Comanda":                     order_id,
                "DataPlasareComanda":          "",   # not available in scenario; enrich separately if needed
                "Sofer":                       v_label,
                "IntervalClient":              interval_str,
                "DataLivrareSolicitataClient": fmt(tw_end_local),
                "TipVehicul":                  v_type,
                "TipProgramSofer":             shift,
                "Cursa":                       cursa_id,
                "DataStartCursa":              fmt(route_start),
                "DataEndCursa":                fmt(route_end),
            })

    return rows


# ── Excel writer ─────────────────────────────────────────────────────────────

def write_excel(rows: list[dict], path: Path) -> None:
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Rezultate"
    ws.freeze_panes = "A2"

    for col, h in enumerate(HEADERS, 1):
        c = ws.cell(row=1, column=col, value=h)
        c.font      = _HEADER_FONT
        c.fill      = _HEADER_FILL
        c.alignment = _CENTER

    for row_i, row in enumerate(rows, 2):
        for col, key in enumerate(HEADERS, 1):
            c = ws.cell(row=row_i, column=col, value=row.get(key, ""))
            c.font      = _BODY_FONT
            c.alignment = _LEFT

    for col in ws.columns:
        width = max(len(str(c.value or "")) for c in col)
        ws.column_dimensions[col[0].column_letter].width = min(width + 3, 30)

    wb.save(path)


# ── Summary printer ──────────────────────────────────────────────────────────

def print_summary(solution: dict, rows: list[dict]) -> None:
    routes   = solution.get("routes", [])
    skipped  = solution.get("skippedShipments", [])
    served   = len(rows)
    n_routes = len(routes)

    print(f"\n{'─' * 52}")
    print(f"  Routes used:      {n_routes}")
    print(f"  Deliveries made:  {served}")
    print(f"  Skipped orders:   {len(skipped)}")

    total_km = sum(
        r.get("metrics", {}).get("travelDistanceMeters", 0) for r in routes
    ) / 1000
    if served and total_km:
        print(f"  Total km:         {total_km:.1f}")
        print(f"  Avg km / order:   {total_km / served:.2f}")
        print(f"  Avg orders/route: {served / n_routes:.1f}")

    if skipped:
        reasons: dict[str, int] = {}
        for s in skipped:
            for r in s.get("reasons", []):
                code = r.get("code", "UNKNOWN")
                reasons[code] = reasons.get(code, 0) + 1
        print(f"\n  Skipped reasons:")
        for code, count in sorted(reasons.items(), key=lambda x: -x[1]):
            print(f"    {code}: {count}")
    print(f"{'─' * 52}\n")


# ── CLI ──────────────────────────────────────────────────────────────────────

def main() -> int:
    parser = argparse.ArgumentParser(
        description="Convert Fleet Routing app export to Freshfull Rezultate Excel."
    )
    src = parser.add_mutually_exclusive_group(required=True)
    src.add_argument("--zip",      help="Path to the ZIP file downloaded from the app")
    src.add_argument("--scenario", help="Path to scenario.json (use with --solution)")
    parser.add_argument("--solution", help="Path to solution.json (required if --scenario is used)")
    parser.add_argument("--output", required=True, help="Output Excel file path (.xlsx)")
    args = parser.parse_args()

    # Load scenario + solution
    if args.zip:
        zip_path = Path(args.zip)
        with zipfile.ZipFile(zip_path) as zf:
            names = zf.namelist()
            # Support both "scenario.json" and nested paths
            scen_name = next((n for n in names if n.endswith("scenario.json")), None)
            sol_name  = next((n for n in names if n.endswith("solution.json")), None)
            if not scen_name or not sol_name:
                print(f"[from_app_json] ERROR: ZIP must contain scenario.json and solution.json. Found: {names}")
                return 1
            scenario = json.loads(zf.read(scen_name))
            solution = json.loads(zf.read(sol_name))
        print(f"[from_app_json] Loaded from {zip_path.name}")
    else:
        if not args.solution:
            print("[from_app_json] ERROR: --solution is required when using --scenario")
            return 1
        scenario = json.loads(Path(args.scenario).read_text())
        solution = json.loads(Path(args.solution).read_text())
        print(f"[from_app_json] Loaded scenario + solution JSON files")

    rows = build_rows(scenario, solution)
    print_summary(solution, rows)

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    write_excel(rows, output_path)
    print(f"[from_app_json] Saved {len(rows)} rows to {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
