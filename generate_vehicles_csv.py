#!/usr/bin/env python3
"""
Generate vehicles CSV with simple configurations.
All vehicles will be available, driving mode, return to depot, no costs.
"""

import csv
import argparse


def generate_vehicles_csv(
    output_path: str,
    num_vehicles: int = 5,
    depot_lat: float = 44.5279615,
    depot_lon: float = 26.1798147,
    capacity_pallets: int = 100,
    use_if_empty: bool = False
) -> None:
    """
    Generate a vehicles CSV file with simple configurations.
    
    Args:
        output_path: Path to output CSV file
        num_vehicles: Number of vehicles to generate
        depot_lat: Depot latitude
        depot_lon: Depot longitude
        capacity_pallets: Capacity in pallets per vehicle
        use_if_empty: Whether vehicle should be used if route is empty (default: False)
    """
    
    # CSV headers
    headers = [
        'label',
        'travelMode',
        'startWaypoint',
        'endWaypoint',
        'unloadingPolicy',
        'costPerHour',
        'costPerTraveledHour',
        'costPerKilometer',
        'fixedCost',
        'usedIfRouteIsEmpty',
        'travelDurationMultiple',
        'StartTimeWindowCostPerHourBeforeSoftStartTime',
        'StartTimeWindowCostPerHourAfterSoftEndTime',
        'startTimeWindowStartTime',
        'startTimeWindowSoftStartTime',
        'startTimeWindowEndTime',
        'startTimeWindowSoftEndTime',
        'EndTimeWindowCostPerHourBeforeSoftStartTime',
        'EndTimeWindowCostPerHourAfterSoftEndTime',
        'endTimeWindowStartTime',
        'endTimeWindowSoftStartTime',
        'endTimeWindowEndTime',
        'endTimeWindowSoftEndTime',
        'loadLimit1Type',
        'loadLimit1Value',
        'loadLimit2Type',
        'loadLimit2Value',
        'loadLimit3Type',
        'loadLimit3Value',
        'loadLimit4Type',
        'loadLimit4Value'
    ]
    
    rows = []
    depot_waypoint = f'{depot_lat}, {depot_lon}'
    use_if_empty_str = 'TRUE' if use_if_empty else 'FALSE'
    
    # Generate vehicles
    for i in range(num_vehicles):
        row = {
            'label': f'Vehicle - {i+1}',
            'travelMode': 'DRIVING',
            'startWaypoint': depot_waypoint,
            'endWaypoint': depot_waypoint,
            'unloadingPolicy': 'UNLOADING_POLICY_UNSPECIFIED',
            'costPerHour': '0',
            'costPerTraveledHour': '0',
            'costPerKilometer': '0',
            'fixedCost': '0',
            'usedIfRouteIsEmpty': use_if_empty_str,
            'travelDurationMultiple': '1',
            'StartTimeWindowCostPerHourBeforeSoftStartTime': '',
            'StartTimeWindowCostPerHourAfterSoftEndTime': '',
            'startTimeWindowStartTime': '',
            'startTimeWindowSoftStartTime': '',
            'startTimeWindowEndTime': '',
            'startTimeWindowSoftEndTime': '',
            'EndTimeWindowCostPerHourBeforeSoftStartTime': '',
            'EndTimeWindowCostPerHourAfterSoftEndTime': '',
            'endTimeWindowStartTime': '',
            'endTimeWindowSoftStartTime': '',
            'endTimeWindowEndTime': '',
            'endTimeWindowSoftEndTime': '',
            'loadLimit1Type': 'pallets',
            'loadLimit1Value': str(capacity_pallets),
            'loadLimit2Type': '',
            'loadLimit2Value': '',
            'loadLimit3Type': '',
            'loadLimit3Value': '',
            'loadLimit4Type': '',
            'loadLimit4Value': ''
        }
        rows.append(row)
    
    # Write to CSV
    with open(output_path, 'w', newline='') as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=headers)
        writer.writeheader()
        writer.writerows(rows)
    
    print(f"✓ Generated {num_vehicles} vehicles")
    print(f"✓ Saved to: {output_path}")
    print(f"\nConfiguration:")
    print(f"  Depot: ({depot_lat}, {depot_lon})")
    print(f"  Travel mode: DRIVING")
    print(f"  Costs: $0 (all zero)")
    print(f"  Capacity per vehicle:")
    print(f"    - Pallets: {capacity_pallets}")
    print(f"  Weight: Unlimited")
    print(f"  Time constraints: None (available 24/7)")
    print(f"  Use if empty: {use_if_empty_str.lower()}")
    print(f"\nFirst 3 vehicles:")
    for row in rows[:3]:
        print(f"  {row['label']}: {row['startWaypoint']} → {row['endWaypoint']} ({row['loadLimit1Value']} pallets)")


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Generate vehicles CSV with simple configurations')
    
    parser.add_argument('-o', '--output', default='data/vehicles_generated.csv',
                        help='Output CSV file path (default: data/vehicles_generated.csv)')
    parser.add_argument('-n', '--num-vehicles', type=int, default=5,
                        help='Number of vehicles to generate (default: 5)')
    parser.add_argument('--depot-lat', type=float, default=44.5279615,
                        help='Depot latitude (default: 44.5279615 - Bucharest)')
    parser.add_argument('--depot-lon', type=float, default=26.1798147,
                        help='Depot longitude (default: 26.1798147 - Bucharest)')
    parser.add_argument('--capacity-pallets', type=int, default=100,
                        help='Capacity in pallets per vehicle (default: 100)')
    parser.add_argument('--use-if-empty', action='store_true', default=False,
                        help='Use vehicle even if route is empty (default: False)')
    
    args = parser.parse_args()
    
    generate_vehicles_csv(
        output_path=args.output,
        num_vehicles=args.num_vehicles,
        depot_lat=args.depot_lat,
        depot_lon=args.depot_lon,
        capacity_pallets=args.capacity_pallets,
        use_if_empty=args.use_if_empty
    )
