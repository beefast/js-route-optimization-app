/*
Copyright 2024 Google LLC

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    https://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
*/

import * as fromRoutesMetadata from '../reducers/routes-metadata.reducer';
import { selectRoutesMetadataState, selectRouteMetadata } from './routes-metadata.selectors';

describe('RoutesMetadata Selectors', () => {
  it('should select the feature state', () => {
    const result = selectRoutesMetadataState({
      [fromRoutesMetadata.routesMetadataFeatureKey]: {
        pageIndex: 0,
        pageSize: 25,
        sort: { active: null, direction: null },
        filters: [],
        selected: [],
        displayColumns: null,
      },
    });

    expect(result).toEqual({
      pageIndex: 0,
      pageSize: 25,
      sort: { active: null, direction: null },
      filters: [],
      selected: [],
      displayColumns: null,
    });
  });

  it('computes dropoff-window deliveries rate using visit timestamps', () => {
    // set up minimal entities for a single route with two dropoffs one hour apart
    const routes = {
      1: {
        id: 1,
        visits: [1, 2],
        vehicleStartTime: { seconds: 0 } as any,
        vehicleEndTime: { seconds: 7200 } as any,
        metrics: { travelDistanceMeters: 0 } as any,
      },
    } as any;

    const vehicles = {
      1: {
        startWaypoint: { location: { latLng: {} } },
        endWaypoint: { location: { latLng: {} } },
        loadLimits: {},
      } as any,
    } as any;

    const visits = {
      1: { id: 1, shipmentIndex: 0, isPickup: false, startTime: { seconds: 0 } } as any,
      2: { id: 2, shipmentIndex: 1, isPickup: false, startTime: { seconds: 3600 } } as any,
    } as any;

    const shipments = {} as any;
    const selectedLookup = {} as any;

    const metadata = selectRouteMetadata.projector(routes, vehicles, visits, shipments, selectedLookup);
    expect(metadata.length).toBe(1);
    const meta = metadata[0];
    // two dropoffs spaced 1 hour apart => 2 per hour
    expect(meta.deliveriesPerHourDropoffWindow).toBeCloseTo(2);
  });
});
