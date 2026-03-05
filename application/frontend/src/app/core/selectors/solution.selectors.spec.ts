
import { selectTotalDeliveriesPerHour, selectTotalDeliveriesPerHourDropoffWindow } from './solution.selectors';

// Build a fake routes array similar to the dispatcher solution format
const makeRoute = (visits: any[], start?: number, end?: number) => ({
  visits,
  vehicleStartTime: start != null ? { seconds: start } : null,
  vehicleEndTime: end != null ? { seconds: end } : null,
});

describe('solution selectors', () => {
  it('calculates deliveries per hour using route durations', () => {
    const routes = [
      makeRoute([
        { isPickup: true, startTime: { seconds: 0 } },
        { isPickup: false, startTime: { seconds: 3600 } },
      ], 0, 7200),
      makeRoute([
        { isPickup: false, startTime: { seconds: 0 } },
        { isPickup: false, startTime: { seconds: 1800 } },
      ], 0, 3600),
    ];

    // total dropoffs=3, total duration=(2h +1h)=3h => 1 per hour
    const result = selectTotalDeliveriesPerHour.projector(routes as any);
    expect(result).toBeCloseTo(1);
  });

  it('calculates deliveries per hour using dropoff windows', () => {
    const routes = [
      makeRoute([
        { isPickup: true, startTime: { seconds: 0 } },
        { isPickup: false, startTime: { seconds: 0 } },
        { isPickup: false, startTime: { seconds: 3600 } },
      ]),
      makeRoute([
        { isPickup: false, startTime: { seconds: 0 } },
        { isPickup: false, startTime: { seconds: 1800 } },
      ]),
    ];
    // route1 window=1h with 2 drops; route2 window=0.5h with 2 drops => total drops=4 total window=1.5h => 2.666...
    const result = selectTotalDeliveriesPerHourDropoffWindow.projector(routes as any);
    expect(result).toBeCloseTo(4 / 1.5);
  });
});
