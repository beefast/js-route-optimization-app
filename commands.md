python generate_vehicles_csv.py \
    --output data/vehicles_20.csv \
    --num-vehicles 20


python generate_shipments_csv.py -o data/shipments.csv -n 100 \
    --coords-method curated \
    --curated-file data/curated_dropoff_coords.csv