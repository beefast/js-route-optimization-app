# Freshfull Route Optimization Pipeline

Three scripts that transform the Freshfull Excel data into optimized routes and produce
the required output format.

```
transform.py  →  request.json  →  run_api.py  →  response.json  →  to_output.py  →  rezultate.xlsx
```

## Prerequisites

```bash
pip install openpyxl
```

Authentication:
```bash
gcloud auth login
export PROJECT_ID=your-gcp-project-id
export TOKEN=$(gcloud auth print-access-token)
```

## Step 1 — Build the API request

```bash
# Small sample (cheap, fast — use to validate the mapping)
python -m python.freshfull.transform \
    --input "/Users/marian/Documents/FreshFull/Centralizator 23-29 martie.xlsx" \
    --date 2026-03-23 \
    --sample 50 \
    --vehicles 20 \
    --timeout 60 \
    --output data/freshfull/request_sample.json

# Full day (~4 000 orders, all 167 vehicles)
python -m python.freshfull.transform \
    --input "/Users/marian/Documents/FreshFull/Centralizator 23-29 martie.xlsx" \
    --date 2026-03-23 \
    --high-quality \
    --timeout 600 \
    --output data/freshfull/request_2026-03-23.json
```

## Step 2 — Call the API

```bash
# Sample
python -m python.freshfull.run_api \
    --request data/freshfull/request_sample.json \
    --output  data/freshfull/response_sample.json \
    --project $PROJECT_ID \
    --token   $TOKEN

# Full day
python -m python.freshfull.run_api \
    --request data/freshfull/request_2026-03-23.json \
    --output  data/freshfull/response_2026-03-23.json \
    --project $PROJECT_ID \
    --token   $TOKEN
```

## Step 3 — Convert to output Excel

```bash
python -m python.freshfull.to_output \
    --request  data/freshfull/request_sample.json \
    --response data/freshfull/response_sample.json \
    --output   data/freshfull/rezultate_sample.xlsx
```

## Requirements → API parameter mapping

| Requirement | API field | Notes |
|---|---|---|
| Customer time window (`IntervalClient`) | `shipment.deliveries[0].timeWindows` | Effective start = max(window, placement+125min) |
| 7 min delivery time | `deliveries[0].duration = "420s"` | |
| Order placement + 125 min prep | Shifts `timeWindows[0].startTime` forward | |
| Capacity (ambient / chilled / frozen) | `shipment.loadDemands` | 4th dim: `ambient_chilled` for Iveco/Renault combined hold |
| Iveco: 120-box combined hold | `vehicle.loadLimits.ambient_chilled.maxLoad=120` | |
| Peugeot: 48 ambient + 39 chilled | `vehicle.loadLimits.ambient.maxLoad=48` + `chilled.maxLoad=39` | Separate compartments |
| Renault: 144-box combined hold | `vehicle.loadLimits.ambient_chilled.maxLoad=144` | |
| All vehicles: 14 frozen bags | `vehicle.loadLimits.frozen.maxLoad=14` | |
| Zone 211/31/32 (Peugeot only) | `shipment.allowedVehicleIndices` → Peugeot indices | Parsed from `InfoTipMasinaLivrare` |
| 28 loading docks | Staggered `vehicle.startTimeWindows` in batches of 28 | Each batch: 30-min exclusive slot |
| Driver shift (10h default) | `vehicle.routeDurationLimit.maxDuration="36000s"` | |
| 1h mandatory break | `vehicle.breakRule.breakRequests` | Window: 11:00–16:00 local |
| Skip cost | `shipment.penaltyCost=10000` | High value → optimizer tries to serve all orders |

## Tuning levers

- **`--timeout`**: more time = better solution; 60s for samples, 600s for full day
- **`--high-quality`**: enables `RETURN_HIGH_QUALITY` search mode (much better for production)
- **`PENALTY_COST`** in `transform.py`: raise to force the optimizer to serve more orders at the cost of longer routes
- **`FLEET[*].cost_fixed`** in `transform.py`: raise to force fewer vehicles (denser routes)
- **`BREAK_EARLIEST_HOUR` / `BREAK_LATEST_HOUR`**: shift the break window

## Multi-day run (full week)

Run Steps 1–3 for each date and concatenate the rezultate files, or adapt `to_output.py`
to append to a single workbook. Between days, drivers on a 12h shift must be excluded
from the next day's vehicle list (manual step until we automate it).
