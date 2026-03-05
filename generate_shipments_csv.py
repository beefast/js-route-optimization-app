#!/usr/bin/env python3
"""
Generate shipments CSV with delivery coordinates.
Supports configurable deposits, time windows, and load parameters.
Coordinates may be generated randomly within a square area or sampled without repetition
from a curated list of coordinates (CSV file).
"""

import csv
import random
import argparse
from datetime import datetime, timedelta
from typing import List, Dict, Tuple


def generate_random_coords(center_lat: float, center_lon: float, square_size_km: float) -> Tuple[float, float]:
    """
    Generate random coordinates within a square area.
    
    Args:
        center_lat: Center latitude
        center_lon: Center longitude
        square_size_km: Size of square in kilometers
    
    Returns:
        Tuple of (latitude, longitude)
    """
    # Approximate conversion: 1 degree latitude ≈ 111 km, 1 degree longitude ≈ 111 km * cos(latitude)
    lat_offset = (square_size_km / 2) / 111.0
    lon_offset = (square_size_km / 2) / (111.0 * abs(__import__('math').cos(__import__('math').radians(center_lat))))
    
    lat = center_lat + random.uniform(-lat_offset, lat_offset)
    lon = center_lon + random.uniform(-lon_offset, lon_offset)
    
    return round(lat, 8), round(lon, 8)


def generate_random_time_window(start_hour: int = 11, end_hour: int = 13, window_duration_minutes: int = 60, fixed_hour: int = None, fixed_minute: int = 0) -> Tuple[str, str, str, str]:
    """
    Generate a 1-hour delivery time window from minute 00 (e.g., 13:00 to 14:00).
    
    Args:
        start_hour: Starting hour (default 6)
        end_hour: Ending hour (default 22)
        window_duration_minutes: Duration of time window in minutes (default 60)
        fixed_hour: If provided, use this hour for all windows (for common pickup time)
        fixed_minute: Minute to use with fixed_hour (default 0)
    
    Returns:
        Tuple of (startTime, softStartTime, endTime, softEndTime) in ISO 8601 format
    """
    # Random or fixed hour
    if fixed_hour is not None:
        random_hour = fixed_hour
    else:
        random_hour = random.randint(start_hour, end_hour - 1)
    
    # Base date = tomorrow at minute 00
    tomorrow = datetime.now() + timedelta(days=1)
    base_date = tomorrow.replace(hour=random_hour, minute=0, second=0, microsecond=0)
    
    # Hard window: hour:00 to (hour+1):00
    start_time = base_date
    end_time = base_date + timedelta(minutes=window_duration_minutes)
    
    # Format as ISO 8601
    start_iso = start_time.strftime('%Y-%m-%dT%H:%M:%S.000Z')
    end_iso = end_time.strftime('%Y-%m-%dT%H:%M:%S.000Z')
    
    return start_iso, start_iso, end_iso, end_iso


def generate_shipments_csv(
    output_path: str,
    num_shipments: int = 20,
    depot_lat: float = 44.5279615,
    depot_lon: float = 26.1798147,
    delivery_center_lat: float = 44.4268056,
    delivery_center_lon: float = 26.0999251,
    square_size_km: float = 20.0,
    delivery_duration_sec: int = 600,
    penalty_cost: int = 200,
    penalty_per_hour: int = 1000,
    max_pallets: int = 10,
    seed: int = None,
    pickup_hour: int = None,
    pickup_minute: int = 0,
    window_start_hour: int = 11,
    window_end_hour: int = 13,
    coords_method: str = 'random',
    curated_coords: List[Tuple[float, float]] = None,
    cluster_count: int = 3,
    cluster_spread_km: float = 1.0,
) -> None:
    """
    Generate a shipments CSV file with random delivery locations and time windows.
    
    Args:
        output_path: Path to output CSV file
        num_shipments: Number of shipments to generate
        depot_lat: Depot latitude
        depot_lon: Depot longitude
        square_size_km: Size of the square area around depot in kilometers
        delivery_duration_sec: Duration of each delivery in seconds
        penalty_cost: Penalty cost for missing time window
        penalty_per_hour: Cost per hour for early/late arrival
        max_pallets: Maximum number of pallets per shipment
        seed: Random seed for reproducibility
        pickup_hour: Fixed hour for all pickups (None = random per order)
        pickup_minute: Minute for fixed pickup time
        window_start_hour: start of window hour (default 11)
        window_end_hour: end of window hour (default 13; window is [start, end))
        coords_method: Which coordinate strategy to use ('random', 'curated', 'cluster')
        curated_coords: list of coords when using curated method (ignored otherwise)
        cluster_count: number of cluster centers (used only for cluster method)
        cluster_spread_km: spread size in km around each cluster center
        delivery_center_lat: Latitude of the delivery area center (default: 44.4268056)
        delivery_center_lon: Longitude of the delivery area center (default: 26.0999251)
    """
    
    if seed is not None:
        random.seed(seed)

    # prepare coordinate pool depending on the method
    coords_pool = None
    if coords_method == 'curated':
        if curated_coords is None:
            raise ValueError('coords_method is curated but no curated_coords supplied')
        coords_pool = curated_coords.copy()
        random.shuffle(coords_pool)
    elif coords_method == 'cluster':
        # generate a predetermined list of clustered coordinates
        coords_pool = generate_clustered_coords(
            num_shipments,
            delivery_center_lat,
            delivery_center_lon,
            square_size_km,
            cluster_count,
            cluster_spread_km,
        )
    # else coords_pool stays None and random points will be generated in loop
    
    # CSV headers
    headers = [
        'label',
        'penaltyCost',
        'pickupArrivalWaypoint',
        'pickupDuration',
        'pickupCost',
        'pickupStartTime',
        'pickupSoftStartTime',
        'pickupEndTime',
        'pickupSoftEndTime',
        'pickupCostPerHourBeforeSoftStartTime',
        'pickupCostPerHourAfterSoftStartTime',
        'pickupCostPerHourAfterSoftEndTime',
        'deliveryArrivalWaypoint',
        'deliveryDuration',
        'deliveryCost',
        'deliveryStartTime',
        'deliverySoftStartTime',
        'deliveryEndTime',
        'deliverySoftEndTime',
        'deliveryCostPerHourBeforeSoftStartTime',
        'deliveryCostPerHourAfterSoftEndTime',
        'loadDemand1Type',
        'loadDemand1Value',
        'loadDemand2Type',
        'loadDemand2Value',
        'loadDemand3Type',
        'loadDemand3Value',
        'loadDemand4Type',
        'loadDemand4Value',
        'allowedVehicleIndices'
    ]
    
    rows = []
    
    # Generate shipments
    for i in range(num_shipments):
        # Determine delivery location
        if coords_pool is not None:
            if not coords_pool:
                raise ValueError("Coordinate pool exhausted before generating all shipments")
            delivery_lat, delivery_lon = coords_pool.pop()
        else:
            delivery_lat, delivery_lon = generate_random_coords(delivery_center_lat, delivery_center_lon, square_size_km)
        
        # Generate random time window (or fixed pickup time)
        start_time, soft_start, end_time, soft_end = generate_random_time_window(
            start_hour=window_start_hour,
            end_hour=window_end_hour,
            fixed_hour=pickup_hour,
            fixed_minute=pickup_minute,
        )
        
        # Generate random number of pallets
        num_pallets = random.randint(1, max_pallets)
        
        row = {
            'label': f'Order - {i+1}',
            'penaltyCost': str(penalty_cost),
            'pickupArrivalWaypoint': f'{depot_lat}, {depot_lon}',
            'pickupDuration': '0',
            'pickupCost': '',
            'pickupStartTime': '',
            'pickupSoftStartTime': '',
            'pickupEndTime': '',
            'pickupSoftEndTime': '',
            'pickupCostPerHourBeforeSoftStartTime': '',
            'pickupCostPerHourAfterSoftStartTime': '',
            'pickupCostPerHourAfterSoftEndTime': '',
            'deliveryArrivalWaypoint': f'{delivery_lat}, {delivery_lon}',
            'deliveryDuration': str(delivery_duration_sec),
            'deliveryCost': '',
            'deliveryStartTime': start_time,
            'deliverySoftStartTime': soft_start,
            'deliveryEndTime': end_time,
            'deliverySoftEndTime': soft_end,
            'deliveryCostPerHourBeforeSoftStartTime': str(penalty_per_hour),
            'deliveryCostPerHourAfterSoftEndTime': str(penalty_per_hour),
            'loadDemand1Type': 'pallets',
            'loadDemand1Value': str(num_pallets),
            'loadDemand2Type': '',
            'loadDemand2Value': '',
            'loadDemand3Type': '',
            'loadDemand3Value': '',
            'loadDemand4Type': '',
            'loadDemand4Value': '',
            'allowedVehicleIndices': ''
        }
        rows.append(row)
    
    # Write to CSV
    with open(output_path, 'w', newline='') as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=headers)
        writer.writeheader()
        writer.writerows(rows)
    
    print(f"✓ Generated {num_shipments} shipments")
    print(f"✓ Saved to: {output_path}")
    print(f"\nConfiguration:")
    print(f"  Depot: ({depot_lat}, {depot_lon})")
    print(f"  Coord method: {coords_method}")
    if coords_method == 'curated':
        print(f"  Curated coords count: {len(curated_coords) if curated_coords else 0}")
    elif coords_method == 'cluster':
        print(f"  Clusters: {cluster_count}, spread {cluster_spread_km}km")


def load_curated_coords(file_path: str) -> List[Tuple[float, float]]:
    """Load latitude/longitude pairs from a CSV file with headers 'latitude,longitude'."""
    coords = []
    with open(file_path, newline='') as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            try:
                lat = float(row['latitude'])
                lon = float(row['longitude'])
                coords.append((lat, lon))
            except (KeyError, ValueError):
                continue
    return coords


def generate_clustered_coords(
    num_points: int,
    center_lat: float,
    center_lon: float,
    square_size_km: float,
    num_clusters: int = 3,
    cluster_spread_km: float = 1.0,
) -> List[Tuple[float, float]]:
    """Generate a specified number of points concentrated around a handful of cluster centers.

    Clusters themselves are placed randomly within a square area centered at the
    delivery center. Each generated point is uniformly placed within a small square
    around its assigned cluster center (spread given in km).

    Args:
        num_points: total number of coordinates to produce
        center_lat, center_lon: location of delivery area center used for sampling
        square_size_km: bounding square size in kilometers for cluster centers
        num_clusters: number of clusters to create
        cluster_spread_km: size of the square (in km) around each cluster center
            within which individual orders will be distributed.

    Returns:
        List of (lat, lon) tuples of length num_points.
    """
    # create cluster centers
    clusters: List[Tuple[float, float]] = []
    for _ in range(num_clusters):
        clusters.append(generate_random_coords(center_lat, center_lon, square_size_km))

    points: List[Tuple[float, float]] = []
    for _ in range(num_points):
        # pick a random cluster
        clat, clon = random.choice(clusters)
        # generate a point near the cluster center using smaller square
        plat, plon = generate_random_coords(clat, clon, cluster_spread_km)
        points.append((plat, plon))

    # shuffle so sequential popping in the main loop yields random distribution
    random.shuffle(points)
    return points


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate shipments CSV with random or curated delivery coordinates")
    parser.add_argument('--output', '-o', required=True, help='Output CSV path')
    parser.add_argument('--count', '-n', type=int, default=20, help='Number of shipments')
    parser.add_argument('--depot-lat', type=float, default=44.5279615)
    parser.add_argument('--depot-lon', type=float, default=26.1798147)
    parser.add_argument('--delivery-center-lat', type=float, default=44.4268056)
    parser.add_argument('--delivery-center-lon', type=float, default=26.0999251)
    parser.add_argument('--square-size-km', type=float, default=20.0)
    parser.add_argument('--pallets', type=int, default=10, help='Maximum pallets per shipment')
    parser.add_argument('--seed', type=int, help='Random seed')
    parser.add_argument('--pickup-hour', type=int, help='Fixed pickup hour (0-23)')
    parser.add_argument('--pickup-minute', type=int, default=0, help='Fixed pickup minute')
    parser.add_argument('--window-start-hour', type=int, default=11,
                        help='Minimum hour (included) for random delivery window start; default 11')
    parser.add_argument('--window-end-hour', type=int, default=13,
                        help='Maximum hour (excluded) for random delivery window start; default 13')
    parser.add_argument('--coords-method', choices=['random', 'curated', 'cluster'], default='random',
                        help='Coordinate generation method: random within square, curated from file, or cluster-based')
    parser.add_argument('--curated-file', help='Path to CSV file containing curated coordinates')
    parser.add_argument('--cluster-count', type=int, default=3,
                        help='Number of clusters when using cluster mode')
    parser.add_argument('--cluster-spread-km', type=float, default=1.0,
                        help='Spread radius (km) for each cluster in cluster mode')
    args = parser.parse_args()

    if args.coords_method == 'curated' and not args.curated_file:
        parser.error('coords-method curated requires --curated-file')

    return args

    return args


def main():
    args = parse_args()

    curated_coords = None
    if args.coords_method == 'curated':
        curated_coords = load_curated_coords(args.curated_file)
        if len(curated_coords) < args.count:
            raise ValueError(f"Curated file contains only {len(curated_coords)} coords but {args.count} shipments requested")

    generate_shipments_csv(
        output_path=args.output,
        num_shipments=args.count,
        depot_lat=args.depot_lat,
        depot_lon=args.depot_lon,
        delivery_center_lat=args.delivery_center_lat,
        delivery_center_lon=args.delivery_center_lon,
        square_size_km=args.square_size_km,
        max_pallets=args.pallets,
        seed=args.seed,
        pickup_hour=args.pickup_hour,
        pickup_minute=args.pickup_minute,
        window_start_hour=args.window_start_hour,
        window_end_hour=args.window_end_hour,
        coords_method=args.coords_method,
        curated_coords=curated_coords,
        cluster_count=args.cluster_count,
        cluster_spread_km=args.cluster_spread_km,
    )


if __name__ == '__main__':
    main()
