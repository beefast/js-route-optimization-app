#!/usr/bin/env python3
"""
Generate shipments CSV with random delivery coordinates in a square area.
Supports configurable deposits, time windows, and load parameters.
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


def generate_random_time_window(start_hour: int = 6, end_hour: int = 22, window_duration_minutes: int = 60, fixed_hour: int = None, fixed_minute: int = 0) -> Tuple[str, str, str, str]:
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
    pickup_minute: int = 0
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
        delivery_center_lat: Latitude of the delivery area center (default: 44.4268056)
        delivery_center_lon: Longitude of the delivery area center (default: 26.0999251)
    """
    
    if seed is not None:
        random.seed(seed)
    
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
        # Generate random delivery location around delivery center
        delivery_lat, delivery_lon = generate_random_coords(delivery_center_lat, delivery_center_lon, square_size_km)
        
        # Generate random time window (or fixed pickup time)
        start_time, soft_start, end_time, soft_end = generate_random_time_window(fixed_hour=pickup_hour, fixed_minute=pickup_minute)
        
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
    print(f"  Square area: {square_size_km}km")
    print(f"  Delivery duration: {delivery_duration_sec}s ({delivery_duration_sec//60}m)")
    print(f"  Penalty cost: {penalty_cost}")
    print(f"  Penalty per hour: {penalty_per_hour}")
    print(f"  Max pallets: {max_pallets}")
    print(f"  Delivery center: ({delivery_center_lat}, {delivery_center_lon})")
    print(f"\nFirst 3 records:")
    for row in rows[:3]:
        print(f"  {row['label']}: ({row['deliveryArrivalWaypoint']}) @ {row['deliveryStartTime']} ({row['loadDemand1Value']} pallets)")


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Generate shipments CSV with random coordinates and time windows')
    
    parser.add_argument('-o', '--output', default='data/shipments_generated.csv',
                        help='Output CSV file path (default: data/shipments_generated.csv)')
    parser.add_argument('-n', '--num-shipments', type=int, default=20,
                        help='Number of shipments to generate (default: 20)')
    parser.add_argument('--depot-lat', type=float, default=44.5279615,
                        help='Depot latitude (default: 44.5279615 - Bucharest)')
    parser.add_argument('--depot-lon', type=float, default=26.1798147,
                        help='Depot longitude (default: 26.1798147 - Bucharest)')
    parser.add_argument('--square-size', type=float, default=20.0,
                        help='Square area size in kilometers (default: 20.0)')
    parser.add_argument('--delivery-duration', type=int, default=600,
                        help='Delivery duration in seconds (default: 600 = 10 minutes)')
    parser.add_argument('--penalty-cost', type=int, default=200,
                        help='Penalty cost for missed time window (default: 200)')
    parser.add_argument('--penalty-per-hour', type=int, default=1000,
                        help='Cost per hour for early/late arrival (default: 1000)')
    parser.add_argument('--max-pallets', type=int, default=10,
                        help='Maximum number of pallets per shipment (default: 10)')
    parser.add_argument('--seed', type=int, default=None,
                        help='Random seed for reproducibility (default: None)')
    parser.add_argument('--pickup-hour', type=int, default=None,
                        help='Fixed hour for all pickups (None = random; e.g. 8 for 8 AM)')
    parser.add_argument('--pickup-minute', type=int, default=0,
                        help='Minute for fixed pickup time (default: 0)')
    parser.add_argument('--delivery-center-lat', type=float, default=44.4268056,
                        help='Delivery area center latitude (default: 44.4268056)')
    parser.add_argument('--delivery-center-lon', type=float, default=26.0999251,
                        help='Delivery area center longitude (default: 26.0999251)')
    
    args = parser.parse_args()
    
    generate_shipments_csv(
        output_path=args.output,
        num_shipments=args.num_shipments,
        depot_lat=args.depot_lat,
        depot_lon=args.depot_lon,
        delivery_center_lat=args.delivery_center_lat,
        delivery_center_lon=args.delivery_center_lon,
        square_size_km=args.square_size,
        delivery_duration_sec=args.delivery_duration,
        penalty_cost=args.penalty_cost,
        penalty_per_hour=args.penalty_per_hour,
        max_pallets=args.max_pallets,
        seed=args.seed,
        pickup_hour=args.pickup_hour,
        pickup_minute=args.pickup_minute
    )
