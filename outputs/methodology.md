# Coimbatore public amenities — mapathon submission

## Intended question

Where are mapped public amenities located, and which parts of the urban study
frame are more than 400 m or 800 m from the nearest mapped facility?

## Data and reproducibility

- Source: OpenStreetMap contributors, queried through Overpass API.
- Snapshot: 2026-09-09 16:36 UTC.
- Study frame: `10.9,76.82,11.12,77.1`
  (south, west, north, east).
- Categories: health, education, civic & safety, community, recreation,
  mobility and other public amenities.
- The raw API responses are retained in `../data/` and the point layer is
  available as `amenities.geojson`.

## Accessibility method

The analysis grid is regular and unweighted. For every grid cell, the nearest
mapped amenity is measured in a local metre approximation. The 400 m and 800 m
thresholds are screening bands, not walking-route distances. The reported
percentages therefore describe *grid proximity to mapped OSM facilities*, not
population access, service adequacy or travel time.

## Responsible interpretation

An apparent gap can reflect incomplete mapping, a physical barrier, a private
facility that is not public-facing, or a real service deficit. Before policy
use, intersect the layer with ward population, run a pedestrian network model,
check opening hours and capacity, and validate priority areas in the field.

## Cartographic standard

The final board includes a title, study location, legend, north arrow, scale
bar, source/attribution, snapshot date, thresholds, metric definitions and
limitations. This keeps the map visually useful while making its claims
auditable.
