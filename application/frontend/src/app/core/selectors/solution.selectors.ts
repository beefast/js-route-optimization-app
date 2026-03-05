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

import { createSelector } from '@ngrx/store';
import Long from 'long';
import { durationSeconds } from 'src/app/util';
import * as fromDispatcher from './dispatcher.selectors';

export const selectHasSolution = createSelector(
  fromDispatcher.selectSolution,
  (solution) => solution != null
);

export const selectSkippedShipments = createSelector(
  fromDispatcher.selectSolution,
  (solution) => solution?.skippedShipments || []
);

export const selectTotalCost = createSelector(
  fromDispatcher.selectSolution,
  (solution) => solution?.metrics?.totalCost || 0
);

export const selectRoutes = createSelector(
  fromDispatcher.selectSolution,
  (solution) => solution?.routes || []
);

export const selectUsedRoutesCount = createSelector(
  selectRoutes,
  (routes) => routes.filter((route) => route.transitions?.length).length
);

export const selectTotalRoutesDistanceMeters = createSelector(selectRoutes, (routes) => {
  let totalDistanceMeters = 0;
  routes.forEach((route) =>
    route.transitions?.forEach(
      (transition) => (totalDistanceMeters += transition.travelDistanceMeters || 0)
    )
  );
  return totalDistanceMeters;
});

// compute deliveries per hour across all routes using vehicle start/end times
export const selectTotalDeliveriesPerHour = createSelector(selectRoutes, (routes) => {
  let totalDropoffs = 0;
  let totalSeconds = 0;
  routes.forEach((route) => {
    if (!route.visits) {
      return;
    }
    const drops = route.visits.filter((v) => !v.isPickup).length;
    totalDropoffs += drops;
    if (route.vehicleStartTime && route.vehicleEndTime) {
      // duration may be IDuration or ITimestamp
      const start = durationSeconds(route.vehicleStartTime);
      const end = durationSeconds(route.vehicleEndTime);
      totalSeconds += end.subtract(start).toNumber();
    }
  });
  return totalSeconds > 0 ? totalDropoffs / (totalSeconds / 3600) : 0;
});

// compute deliveries per hour using the span between first and last dropoff of each route
export const selectTotalDeliveriesPerHourDropoffWindow = createSelector(
  selectRoutes,
  (routes) => {
    let totalDropoffs = 0;
    let totalWindowSeconds = 0;
    routes.forEach((route) => {
      if (!route.visits) {
        return;
      }
      const dropTimes: Long[] = [];
      route.visits.forEach((v) => {
        if (!v.isPickup && v.startTime) {
          dropTimes.push(durationSeconds(v.startTime));
        }
      });
      if (dropTimes.length > 1) {
        const first = dropTimes.reduce((a, b) => (a.lessThan(b) ? a : b));
        const last = dropTimes.reduce((a, b) => (a.greaterThan(b) ? a : b));
        const windowSeconds = last.subtract(first).toNumber();
        if (windowSeconds > 0) {
          totalDropoffs += dropTimes.length;
          totalWindowSeconds += windowSeconds;
        }
      }
    });
    return totalWindowSeconds > 0 ? totalDropoffs / (totalWindowSeconds / 3600) : 0;
  }
);
