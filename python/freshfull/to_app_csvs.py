#!/usr/bin/env python3
"""
Convert Freshfull delivery data (Excel) into the CSV import format for the Fleet Routing app.

Produces two files:
  - shipments.csv   — one row per order, matches app's shipments import format
  - vehicles.csv    — one row per vehicle (fleet), matches app's vehicles import format

Then in the app: import both CSVs → configure search mode + timeout → run optimization →
download the scenario ZIP → run from_app_json.py to produce Rezultate Excel.

NOTE: Break rules cannot be set via CSV import. After importing, manually configure
break rules in the app (Settings → Vehicles → Break Rule): earliest 11:00, latest 16:00,
duration 1 hour.

Usage:
    # Small sample for cheap testing
    python -m python.freshfull.to_app_csvs \\
        --input "Centralizator 23-29 martie.xlsx" \\
        --date 2026-03-23 \\
        --sample 50 --vehicles 20 \\
        --outdir data/freshfull/sample/

    # Full day
    python -m python.freshfull.to_app_csvs \\
        --input "Centralizator 23-29 martie.xlsx" \\
        --date 2026-03-23 \\
        --outdir data/freshfull/2026-03-23/
"""

import argparse
import csv
import math
from datetime import datetime, timedelta, timezone
from pathlib import Path

import openpyxl

# ── Constants ────────────────────────────────────────────────────────────────

DEPOT_LAT = 44.52655539645606
DEPOT_LON = 26.18054083552211
DEPOT_WAYPOINT = f"{DEPOT_LAT}, {DEPOT_LON}"

UTC_OFFSET_HOURS = 2          # Romania EET (UTC+2 in winter/spring)
DELIVERY_DURATION_S = 420     # 7 min per customer stop
PREP_MINUTES = 125            # order placement → earliest delivery
GLOBAL_START_HOUR = 6         # 06:00 local
GLOBAL_END_HOUR = 23          # 23:00 local
PENALTY_COST = 10_000         # high → optimizer tries to serve all orders

LOADING_DOCKS = 28            # max vehicles loading simultaneously
BATCH_WINDOW_MIN = 30         # each dock batch gets a 30-min exclusive start slot

# Fleet: Iveco then Peugeot then Renault (order determines CSV row index)
FLEET = [
    {
        "type": "Iveco",
        "prefix": "IV",
        "count": 70,
        "cost_fixed": 120.0,
        "cost_per_hour": 60.0,
        "cost_per_km": 2.0,
        "shift_hours": 10,
        # Combined hold: ambient+chilled ≤ 120, frozen ≤ 14
        "limits": [
            ("ambient_chilled", 120),
            ("frozen",          14),
            ("ambient",         9999),
            ("chilled",         9999),
        ],
    },
    {
        "type": "Peugeot",
        "prefix": "PG",
        "count": 85,
        "cost_fixed": 100.0,
        "cost_per_hour": 50.0,
        "cost_per_km": 1.5,
        "shift_hours": 10,
        # Separate compartments: ambient ≤ 48, chilled ≤ 39, frozen ≤ 14
        "limits": [
            ("ambient",         48),
            ("chilled",         39),
            ("frozen",          14),
            ("ambient_chilled", 9999),
        ],
    },
    {
        "type": "Renault",
        "prefix": "RN",
        "count": 12,
        "cost_fixed": 150.0,
        "cost_per_hour": 70.0,
        "cost_per_km": 2.5,
        "shift_hours": 10,
        # Combined hold: ambient+chilled ≤ 144, frozen ≤ 14
        "limits": [
            ("ambient_chilled", 144),
            ("frozen",          14),
            ("ambient",         9999),
            ("chilled",         9999),
        ],
    },
]

# CSV column headers — must match the app's import format exactly
SHIPMENT_HEADERS = [
    "label", "penaltyCost",
    "pickupArrivalWaypoint", "pickupDuration", "pickupCost",
    "pickupStartTime", "pickupSoftStartTime", "pickupEndTime", "pickupSoftEndTime",
    "pickupCostPerHourBeforeSoftStartTime", "pickupCostPerHourAfterSoftEndTime",
    "deliveryArrivalWaypoint", "deliveryDuration", "deliveryCost",
    "deliveryStartTime", "deliverySoftStartTime", "deliveryEndTime", "deliverySoftEndTime",
    "deliveryCostPerHourBeforeSoftStartTime", "deliveryCostPerHourAfterSoftEndTime",
    "loadDemand1Type", "loadDemand1Value",
    "loadDemand2Type", "loadDemand2Value",
    "loadDemand3Type", "loadDemand3Value",
    "loadDemand4Type", "loadDemand4Value",
    "allowedVehicleIndices",
]

VEHICLE_HEADERS = [
    "label", "travelMode", "startWaypoint", "endWaypoint", "unloadingPolicy",
    "costPerHour", "costPerTraveledHour", "costPerKilometer", "fixedCost",
    "usedIfRouteIsEmpty", "travelDurationMultiple",
    "StartTimeWindowCostPerHourBeforeSoftStartTime", "StartTimeWindowCostPerHourAfterSoftEndTime",
    "startTimeWindowStartTime", "startTimeWindowSoftStartTime",
    "startTimeWindowEndTime",   "startTimeWindowSoftEndTime",
    "EndTimeWindowCostPerHourBeforeSoftStartTime", "EndTimeWindowCostPerHourAfterSoftEndTime",
    "endTimeWindowStartTime",   "endTimeWindowSoftStartTime",
    "endTimeWindowEndTime",     "endTimeWindowSoftEndTime",
    "loadLimit1Type", "loadLimit1Value",
    "loadLimit2Type", "loadLimit2Value",
    "loadLimit3Type", "loadLimit3Value",
    "loadLimit4Type", "loadLimit4Value",
]


# ── Time helpers ─────────────────────────────────────────────────────────────

def _tz() -> timezone:
    return timezone(timedelta(hours=UTC_OFFSET_HOURS))


def excel_to_utc(value) -> datetime:
    if isinstance(value, datetime):
        dt = value.replace(tzinfo=_tz()) if value.tzinfo is None else value
    elif isinstance(value, (int, float)):
        dt = (datetime(1899, 12, 30) + timedelta(days=float(value))).replace(tzinfo=_tz())
    else:
        raise ValueError(f"Cannot convert {type(value).__name__} to datetime: {value!r}")
    return dt.astimezone(timezone.utc)


def iso(dt: datetime) -> str:
    """Format UTC datetime as ISO 8601 with milliseconds (app import format)."""
    return dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.000Z")


def local_utc(date, hour: int, minute: int = 0) -> datetime:
    return datetime(date.year, date.month, date.day, hour, minute, tzinfo=_tz()).astimezone(timezone.utc)


# ── Vehicle CSV generation ───────────────────────────────────────────────────

def build_vehicle_rows(date, max_count: int | None = None) -> tuple[list[dict], dict[str, list[int]]]:
    """
    Build vehicle CSV rows and return a type→row-index mapping.
    Row index = position in CSV (0-based) = vehicle index in the app.
    """
    total_fleet = sum(s["count"] for s in FLEET)
    rows: list[dict] = []
    type_index: dict[str, list[int]] = {s["type"]: [] for s in FLEET}

    for spec in FLEET:
        count = spec["count"]
        if max_count is not None:
            count = max(1, round(spec["count"] / total_fleet * max_count))

        for i in range(count):
            if max_count is not None and len(rows) >= max_count:
                break

            vid = len(rows)
            type_index[spec["type"]].append(vid)

            # Stagger departure into dock batches of LOADING_DOCKS vehicles
            batch = vid // LOADING_DOCKS
            slot_start = local_utc(date, GLOBAL_START_HOUR) + timedelta(minutes=batch * BATCH_WINDOW_MIN)
            slot_end   = slot_start + timedelta(minutes=BATCH_WINDOW_MIN - 1)

            # End window: latest start + shift hours + 1h slack
            end_earliest = slot_start + timedelta(hours=spec["shift_hours"] - 1)
            end_latest   = slot_end   + timedelta(hours=spec["shift_hours"] + 1)
            # Cap at global end
            global_end = local_utc(date, GLOBAL_END_HOUR)
            end_latest = min(end_latest, global_end)
            end_earliest = min(end_earliest, global_end)

            limits = spec["limits"]  # list of (type, value) tuples, always length 4

            row = {
                "label":                   f"{spec['prefix']}-{i + 1:03d}",
                "travelMode":              "DRIVING",
                "startWaypoint":           DEPOT_WAYPOINT,
                "endWaypoint":             DEPOT_WAYPOINT,
                "unloadingPolicy":         "UNLOADING_POLICY_UNSPECIFIED",
                "costPerHour":             spec["cost_per_hour"],
                "costPerTraveledHour":     "",
                "costPerKilometer":        spec["cost_per_km"],
                "fixedCost":               spec["cost_fixed"],
                "usedIfRouteIsEmpty":      "FALSE",
                "travelDurationMultiple":  "",
                "StartTimeWindowCostPerHourBeforeSoftStartTime": "",
                "StartTimeWindowCostPerHourAfterSoftEndTime":    "",
                "startTimeWindowStartTime": iso(slot_start),
                "startTimeWindowSoftStartTime": "",
                "startTimeWindowEndTime":   iso(slot_end),
                "startTimeWindowSoftEndTime": "",
                "EndTimeWindowCostPerHourBeforeSoftStartTime":   "",
                "EndTimeWindowCostPerHourAfterSoftEndTime":      "",
                "endTimeWindowStartTime":   iso(end_earliest),
                "endTimeWindowSoftStartTime": "",
                "endTimeWindowEndTime":     iso(end_latest),
                "endTimeWindowSoftEndTime": "",
                "loadLimit1Type":  limits[0][0], "loadLimit1Value": limits[0][1],
                "loadLimit2Type":  limits[1][0], "loadLimit2Value": limits[1][1],
                "loadLimit3Type":  limits[2][0], "loadLimit3Value": limits[2][1],
                "loadLimit4Type":  limits[3][0], "loadLimit4Value": limits[3][1],
            }
            rows.append(row)

    return rows, type_index


# ── Shipment CSV generation ──────────────────────────────────────────────────

def _is_restricted(vehicle_info: str) -> bool:
    """True if order can only be served by Peugeot (restricted zone)."""
    lower = str(vehicle_info or "").lower()
    return bool(lower) and "toate" not in lower


def build_shipment_rows(
    excel_rows: list[dict],
    peugeot_indices: list[int],
    date,
) -> list[dict]:
    rows = []
    for r in excel_rows:
        order_id = str(r["IdComanda"]).strip()
        lat = float(r["Coordonate.geo_lat"])
        lon = float(r["Coordonate.geo_long"])

        ambient = math.ceil(float(r["CapacitatePlanificataZonaAmbient"] or 0))
        chilled = math.ceil(float(r["CapacitatePlanificataZonaChilled"] or 0))
        frozen  = math.ceil(float(r["CapacitatePlanificataZonaFrozen"]  or 0))
        combined = ambient + chilled

        tw_start = excel_to_utc(r["DataStartLivrareIntervalClient"])
        tw_end   = excel_to_utc(r["DataEndLivrareIntervalClient"])

        order_placed = excel_to_utc(r["Data_plasare_comanda"])
        earliest = order_placed + timedelta(minutes=PREP_MINUTES)
        effective_start = max(tw_start, earliest)
        if effective_start >= tw_end:
            effective_start = tw_end - timedelta(minutes=1)

        vehicle_info = str(r.get("InfoTipMasinaLivrare") or "")
        allowed = ""
        if _is_restricted(vehicle_info) and peugeot_indices:
            allowed = ",".join(str(i) for i in peugeot_indices)

        row = {
            "label":        order_id,
            "penaltyCost":  PENALTY_COST,
            # Pickup fields — empty (delivery-only orders)
            "pickupArrivalWaypoint": "", "pickupDuration": "", "pickupCost": "",
            "pickupStartTime": "", "pickupSoftStartTime": "",
            "pickupEndTime":   "", "pickupSoftEndTime":   "",
            "pickupCostPerHourBeforeSoftStartTime": "",
            "pickupCostPerHourAfterSoftEndTime":    "",
            # Delivery
            "deliveryArrivalWaypoint": f"{lat}, {lon}",
            "deliveryDuration":        DELIVERY_DURATION_S,
            "deliveryCost":            "",
            "deliveryStartTime":       iso(effective_start),
            "deliverySoftStartTime":   "",
            "deliveryEndTime":         iso(tw_end),
            "deliverySoftEndTime":     "",
            "deliveryCostPerHourBeforeSoftStartTime": "",
            "deliveryCostPerHourAfterSoftEndTime":    "",
            # Load demands — 4 dimensions
            "loadDemand1Type": "ambient_chilled", "loadDemand1Value": combined,
            "loadDemand2Type": "ambient",          "loadDemand2Value": ambient,
            "loadDemand3Type": "chilled",          "loadDemand3Value": chilled,
            "loadDemand4Type": "frozen",           "loadDemand4Value": frozen,
            "allowedVehicleIndices": allowed,
        }
        rows.append(row)
    return rows


# ── Excel reader ─────────────────────────────────────────────────────────────

def read_excel(path: Path, target_date, sample: int | None = None) -> list[dict]:
    wb = openpyxl.load_workbook(path, read_only=True, data_only=True)
    ws = wb.active
    headers = [c.value for c in next(ws.iter_rows(min_row=1, max_row=1))]

    rows = []
    for raw in ws.iter_rows(min_row=2, values_only=True):
        row = dict(zip(headers, raw))
        val = row.get("DataStartLivrareIntervalClient")
        if val is None:
            continue
        try:
            local_date = excel_to_utc(val).astimezone(_tz()).date()
            if local_date == target_date:
                rows.append(row)
        except (ValueError, TypeError):
            continue
    wb.close()

    if sample and len(rows) > sample:
        step = len(rows) / sample
        rows = [rows[int(i * step)] for i in range(sample)]

    return rows


def write_csv(path: Path, headers: list[str], rows: list[dict]) -> None:
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=headers, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


# ── CLI ──────────────────────────────────────────────────────────────────────

def main() -> int:
    parser = argparse.ArgumentParser(
        description="Convert Freshfull Excel to shipments.csv + vehicles.csv for the Fleet Routing app."
    )
    parser.add_argument("--input",    required=True, help="Path to Centralizator Excel file")
    parser.add_argument("--date",     required=True, help="Date to process (YYYY-MM-DD)")
    parser.add_argument("--outdir",   required=True, help="Output directory")
    parser.add_argument("--sample",   type=int, default=None, help="Limit to N orders (cheap testing)")
    parser.add_argument("--vehicles", type=int, default=None, help="Limit total vehicle count")
    args = parser.parse_args()

    target_date = datetime.strptime(args.date, "%Y-%m-%d").date()
    outdir = Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)

    print(f"[to_app_csvs] Reading orders for {target_date}...")
    excel_rows = read_excel(Path(args.input), target_date, sample=args.sample)
    print(f"[to_app_csvs] {len(excel_rows)} orders loaded")
    if not excel_rows:
        print("[to_app_csvs] ERROR: no orders found for that date.")
        return 1

    print("[to_app_csvs] Building vehicle list...")
    vehicle_rows, type_index = build_vehicle_rows(target_date, max_count=args.vehicles)
    peugeot_indices = type_index["Peugeot"]
    print(f"[to_app_csvs] {len(vehicle_rows)} vehicles "
          f"(Iveco: {len(type_index['Iveco'])}, "
          f"Peugeot: {len(peugeot_indices)}, "
          f"Renault: {len(type_index['Renault'])})")

    print("[to_app_csvs] Building shipment list...")
    shipment_rows = build_shipment_rows(excel_rows, peugeot_indices, target_date)
    restricted = sum(1 for r in shipment_rows if r["allowedVehicleIndices"])
    print(f"[to_app_csvs] {len(shipment_rows)} shipments ({restricted} Peugeot-restricted)")

    vehicles_path  = outdir / "vehicles.csv"
    shipments_path = outdir / "shipments.csv"
    write_csv(vehicles_path,  VEHICLE_HEADERS,  vehicle_rows)
    write_csv(shipments_path, SHIPMENT_HEADERS, shipment_rows)

    print(f"\n[to_app_csvs] Done.")
    print(f"  Vehicles  → {vehicles_path}")
    print(f"  Shipments → {shipments_path}")
    print(f"\nNext steps in the app:")
    print(f"  1. Import vehicles.csv   (Vehicles tab → Import CSV)")
    print(f"  2. Import shipments.csv  (Shipments tab → Import CSV)")
    print(f"  3. Set break rules manually (Settings: earliest 11:00, latest 16:00, 1h)")
    print(f"  4. Set search mode: RETURN_HIGH_QUALITY, timeout: 300-600s")
    print(f"  5. Run optimization → Download scenario ZIP")
    print(f"  6. Run: python -m python.freshfull.from_app_json --zip <downloaded.zip> --output rezultate.xlsx")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
