import { routeMetadataColumns } from './route-metadata-column.model';

describe('routeMetadataColumns configuration', () => {
  it('includes deliveriesPerHour column', () => {
    const col = routeMetadataColumns.find((c) => c.id === 'deliveriesPerHour');
    expect(col).toBeDefined();
    expect(col.label).toContain('Deliveries');
    expect(col.selector).toBeDefined();
    // verify selector returns expected value when provided a context
    const sample = { deliveriesPerHour: 3.5 } as any;
    expect(col.selector(sample)).toEqual(3.5);
  });

  it('includes abbreviated dropoff-window rate column', () => {
    const col = routeMetadataColumns.find((c) => c.id === 'deliveriesPerHourDropoffWindow');
    expect(col).toBeDefined();
    expect(col.label).toContain('dropoff');
    expect(col.selector).toBeDefined();
    const sample = { deliveriesPerHourDropoffWindow: 2 } as any;
    expect(col.selector(sample)).toEqual(2);
  });
});
