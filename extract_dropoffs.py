import json
import csv


def main():
    input_path = "./data/deliveries.json"
    output_path = "./data/curated_dropoff_coords.csv"

    with open(input_path, "r", encoding="utf-8") as f:
        deliveries = json.load(f)

    with open(output_path, "w", newline="", encoding="utf-8") as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(["latitude", "longitude"])
        for d in deliveries:
            try:
                geo = d.get("dropoffPlace", {}).get("geolocation", {})
                lat = geo.get("latitude")
                lng = geo.get("longitude")
                if lat is not None and lng is not None:
                    writer.writerow([lat, lng])
            except Exception:
                # skip malformed entries
                continue

    print(f"Extracted dropoff coordinates to {output_path}")


if __name__ == "__main__":
    main()
