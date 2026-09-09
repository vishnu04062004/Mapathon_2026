# Coimbatore Public Amenities Map

An interactive mapathon project for Coimbatore, Tamil Nadu, showing mapped
public-facing amenities and an auditable proximity screening layer.

The project is a deployable static web application with no backend, database,
API key, or framework runtime required after the data build.

## What the application provides

- Interactive OpenStreetMap basemap with attribution.
- 1,112 mapped amenity records grouped into health, education, civic and
  safety, community, recreation, mobility, and other public categories.
- Official 100-ward boundaries from the supplied government portal KML.
- Toggleable proximity grid, official wards, and road-context layers.
- 400 m and 800 m indicative proximity bands.
- Amenity search with map focus and popup details.
- Category filters and CSV download.
- Responsive desktop and mobile layouts.
- Local, pinned Leaflet assets with no CDN or commercial map API key.

## Run locally

Requirements: Python 3.10+.

~~~powershell
python practice.py
python -m http.server 4173
~~~

Open http://localhost:4173/. The application should be served over HTTP;
opening index.html directly with file:// prevents browsers from loading the
local GeoJSON assets because of same-origin security rules.

## Deploy

The repository can be deployed as a static site to GitHub Pages, Netlify,
Vercel, or any standard web host.

### GitHub Pages

1. Push the repository to GitHub.
2. Open Settings -> Pages.
3. Select Deploy from a branch, choose main, and choose / (root).
4. Save and wait for the Pages URL to become available.

The included .nojekyll file prevents GitHub Pages from ignoring folders that
begin with an underscore.

### Netlify

Import the repository and use the included netlify.toml. Its publish
directory is the repository root and its build command regenerates the data
assets with python practice.py.

### Vercel or another host

Use the repository root as the static output directory. If a build command is
required, run python practice.py before publishing.

## Data and method

The source snapshot was queried from OpenStreetMap through the Overpass API.
The raw responses are retained in data/osm_amenities.json and
data/osm_roads.json. The official portal source is required_map.kml.

The deployable layers are generated as:

- data/amenities.geojson
- data/roads.geojson
- data/grid.geojson
- data/wards.geojson
- data/metrics.json

The proximity layer evaluates the nearest mapped amenity from the centroid of
a regular grid. The 400 m and 800 m thresholds are straight-line screening
distances. The percentages describe proximity to mapped OSM records, not
population access, walking travel time, service capacity, opening hours, or
quality of provision.

The official ward layer contains 100 ward polygons with ward number, zone,
LGD codes, and portal-provided geometry. Population values were not present in
the supplied KML and are not inferred.

### Reference links

- [Coimbatore Corporation Ward Finder](https://coimbatorejunction.in/coimbatore-corporation/)
- [CCMC official delimitation map](https://ccmc.gov.in/wardmap.html)
- [Coimbatore ward number list reference](https://www.scribd.com/document/931435427/Coimbatore-Ward-List)

For policy or planning use, the next analytical upgrade should intersect the
layer with ward population, a pedestrian network, barriers, and facility
capacity. The current limitation is displayed in the application so the map
does not overstate what the data can support.

## Rebuilding the data layer

practice.py is deterministic against the cached OSM snapshot and supplied KML.
It cleans duplicate records, samples road context for performance, converts
the official ward boundaries, computes the proximity grid, writes deployable
GeoJSON layers, and updates outputs/summary.csv.

~~~powershell
python -m py_compile practice.py
python practice.py
~~~

## Repository layout

~~~text
index.html                 Static application entry point
src/app.js                 Map logic, filters, search, and CSV export
src/styles.css             Responsive visual system
data/                      Generated deployable GeoJSON and metrics
required_map.kml           Official portal ward-boundary source
vendor/leaflet/            Pinned local Leaflet runtime and images
practice.py                Reproducible data build
outputs/                   Summary and presentation exports
netlify.toml               Netlify deployment configuration
~~~

## Attribution and license

Map data © OpenStreetMap contributors, available under the Open Database
License (ODbL). Leaflet is distributed under its BSD-2-Clause license. The
project code is provided for educational and mapathon use.
