# Freshfull Route Optimization Pipeline

Two scripts that bridge between the Freshfull Excel data and the Fleet Routing app.

```
to_app_csvs.py                    from_app_json.py
──────────────                    ────────────────
Centralizator   →  shipments.csv  →  [App UI]  →  gmpro_*.zip  →  rezultate.xlsx
    .xlsx        →  vehicles.csv
```

## Prerequisites

```bash
pip install openpyxl
```

## Step 1 — Generate import CSVs

```bash
# Small sample for cheap testing (50 orders, 20 vehicles)
python -m python.freshfull.to_app_csvs \
    --input "Centralizator 23-29 martie.xlsx" \
    --date 2026-03-23 \
    --sample 50 --vehicles 20 \
    --outdir data/freshfull/sample/

# Full day (~4 000 orders, all 167 vehicles)
python -m python.freshfull.to_app_csvs \
    --input "Centralizator 23-29 martie.xlsx" \
    --date 2026-03-23 \
    --outdir data/freshfull/2026-03-23/
```

Produces `shipments.csv` + `vehicles.csv` in the output directory.

## Step 2 — Run optimization in the app

1. Open the Fleet Routing app
2. **Vehicles tab → Import CSV** → select `vehicles.csv`
3. **Shipments tab → Import CSV** → select `shipments.csv`
4. **Settings** → configure manually (not available in CSV):
   - Break rule: earliest **11:00**, latest **16:00**, duration **1h**
   - Search mode: **RETURN_HIGH_QUALITY**
   - Timeout: **300s** (sample) / **600s** (full day)
5. Click **Optimize**
6. When done → **Download** (saves a `gmpro_*.zip`)

## Step 3 — Convert to Rezultate Excel

```bash
# From the downloaded ZIP
python -m python.freshfull.from_app_json \
    --zip  gmpro_20260323120000.zip \
    --output data/freshfull/rezultate_2026-03-23.xlsx

# Or from extracted JSON files
python -m python.freshfull.from_app_json \
    --scenario data/freshfull/scenario.json \
    --solution data/freshfull/solution.json \
    --output   data/freshfull/rezultate_2026-03-23.xlsx
```

## Requirements → CSV field mapping

| Freshfull requirement | Field in CSV |
|---|---|
| Customer time window (`IntervalClient`) | `deliveryStartTime` / `deliveryEndTime` |
| 125 min prep time | `deliveryStartTime` = max(window start, placement + 125 min) |
| 7 min delivery stop | `deliveryDuration = 420` |
| Order skip penalty | `penaltyCost = 10 000` |
| Customer location | `deliveryArrivalWaypoint = "lat, lon"` |
| Zone 211/31/32 → Peugeot only | `allowedVehicleIndices` = Peugeot row indices |
| 28 loading docks | Staggered `startTimeWindowStartTime` in batches of 28 (30-min slots) |
| Shift end constraint | `endTimeWindowStartTime` / `endTimeWindowEndTime` per batch |
| Iveco: 120-box combined hold | `loadLimit1Type=ambient_chilled`, `loadLimit1Value=120` |
| Peugeot: 48 ambient + 39 chilled | `loadLimit1Type=ambient`, `loadLimit2Type=chilled` |
| Renault: 144-box combined hold | `loadLimit1Type=ambient_chilled`, `loadLimit1Value=144` |
| All: 14 frozen bags | `loadLimit2Type=frozen`, `loadLimit2Value=14` |
| 4th load dim (cross-vehicle) | `loadDemand1Type=ambient_chilled` on shipments |

## Multi-day run (full week)

Run Steps 1–3 for each date March 23–29. Between days, manually exclude from vehicles.csv
any drivers who worked a 12h shift the previous day (legal rest requirement).

## Output columns (Rezultate simulare.xlsx)

| Column | Source |
|---|---|
| DataStartLivrare | Visit start time from solution |
| DataEndLivrare | Visit start + 7 min |
| Comanda | Order ID (shipment label) |
| DataPlasareComanda | Not in scenario — enrich from original Excel if needed |
| Sofer | Vehicle label (proxy for driver) |
| IntervalClient | Delivery time window from scenario |
| DataLivrareSolicitataClient | End of customer time window |
| TipVehicul | Inferred from vehicle label prefix (IV/PG/RN) |
| TipProgramSofer | Inferred from start/end window span |
| Cursa | vehicle label + route start time |
| DataStartCursa | vehicleStartTime from solution |
| DataEndCursa | vehicleEndTime from solution |
