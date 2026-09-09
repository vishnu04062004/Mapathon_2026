"""Build deployable Coimbatore Mapathon data assets.

Run:
    python practice.py

The front-end is a static app. This builder normalizes the cached OSM snapshot
into small, explicit GeoJSON layers and a metrics manifest.
"""
from __future__ import annotations

import csv
import json
import math
import xml.etree.ElementTree as ET
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent
SOURCE_AMENITIES = ROOT / "outputs" / "amenities.geojson"
SOURCE_ROADS = ROOT / "data" / "osm_roads.json"
SOURCE_WARDS = ROOT / "required_map.kml"
PUBLIC = ROOT / "data"
BBOX = {"west": 76.82, "south": 10.90, "east": 77.10, "north": 11.12}
CATEGORIES = {
    "health": "Health",
    "education": "Education",
    "civic": "Civic & safety",
    "community": "Community",
    "recreation": "Recreation",
    "mobility": "Mobility",
    "other": "Other",
}
MAJOR_ROADS = {
    "motorway", "trunk", "primary", "secondary", "tertiary",
    "motorway_link", "trunk_link", "primary_link",
    "secondary_link", "tertiary_link",
}


def local_xy(lon: float, lat: float) -> tuple[float, float]:
    lat0 = (BBOX["south"] + BBOX["north"]) / 2
    return (
        (lon - BBOX["west"]) * 111_320 * math.cos(math.radians(lat0)),
        (lat - BBOX["south"]) * 111_320,
    )


def read_amenities() -> list[dict[str, Any]]:
    source = json.loads(SOURCE_AMENITIES.read_text(encoding="utf-8"))
    clean: list[dict[str, Any]] = []
    seen: set[tuple[Any, ...]] = set()
    for feature in source.get("features", []):
        props = feature.get("properties", {})
        coords = feature.get("geometry", {}).get("coordinates", [])
        if len(coords) != 2:
            continue
        item = {
            "osm_id": str(props.get("osm_id") or ""),
            "name": str(props.get("name") or props.get("kind") or "Unnamed mapped amenity"),
            "kind": str(props.get("kind") or "public amenity"),
            "category": str(props.get("category") or "other"),
            "lon": float(coords[0]),
            "lat": float(coords[1]),
        }
        identity = item["osm_id"] or (
            item["name"], item["kind"], round(item["lon"], 7), round(item["lat"], 7)
        )
        if identity in seen:
            continue
        seen.add(identity)
        clean.append(item)
    return clean


def feature_collection(features: list[dict[str, Any]], name: str) -> dict[str, Any]:
    return {
        "type": "FeatureCollection",
        "name": name,
        "license": "OpenStreetMap data © OpenStreetMap contributors, ODbL 1.0",
        "features": features,
    }


def amenities_geojson(amenities: list[dict[str, Any]]) -> dict[str, Any]:
    features = []
    for item in amenities:
        properties = {k: v for k, v in item.items() if k not in {"lon", "lat"}}
        features.append({
            "type": "Feature",
            "properties": properties,
            "geometry": {"type": "Point", "coordinates": [item["lon"], item["lat"]]},
        })
    return feature_collection(features, "Coimbatore mapped public amenities")


def roads_geojson() -> tuple[dict[str, Any], int]:
    raw = json.loads(SOURCE_ROADS.read_text(encoding="utf-8"))
    features = []
    residential_seen = 0
    for element in raw.get("elements", []):
        tags = element.get("tags", {})
        highway = str(tags.get("highway", ""))
        if highway not in MAJOR_ROADS:
            if highway != "residential":
                continue
            residential_seen += 1
            if residential_seen % 8:
                continue
        geometry = element.get("geometry", [])
        if len(geometry) < 2:
            continue
        coordinates = [[float(point["lon"]), float(point["lat"])] for point in geometry]
        features.append({
            "type": "Feature",
            "properties": {
                "highway": highway,
                "name": str(tags.get("name") or "Unnamed road"),
            },
            "geometry": {"type": "LineString", "coordinates": coordinates},
        })
    return feature_collection(features, "Coimbatore road context"), len(features)


def wards_geojson() -> tuple[dict[str, Any], int]:
    """Convert the official portal KML ward layer to deployable GeoJSON."""
    namespace = {"k": "http://www.opengis.net/kml/2.2"}
    root = ET.parse(SOURCE_WARDS).getroot()
    features = []
    for placemark in root.findall(".//k:Placemark", namespace):
        properties = {
            item.attrib.get("name", ""): item.text or ""
            for item in placemark.findall(".//k:SimpleData", namespace)
        }
        polygons = []
        for polygon in placemark.findall(".//k:Polygon", namespace):
            rings = []
            outer = polygon.find("k:outerBoundaryIs/k:LinearRing/k:coordinates", namespace)
            if outer is None or not outer.text:
                continue
            for coordinates in [outer.text] + [
                node.text or ""
                for node in polygon.findall("k:innerBoundaryIs/k:LinearRing/k:coordinates", namespace)
            ]:
                ring = []
                for value in coordinates.split():
                    parts = value.split(",")
                    if len(parts) >= 2:
                        ring.append([float(parts[0]), float(parts[1])])
                if ring:
                    rings.append(ring)
            if rings:
                polygons.append(rings)
        if not polygons:
            continue
        geometry = {"type": "MultiPolygon", "coordinates": polygons}
        features.append({
            "type": "Feature",
            "properties": properties,
            "geometry": geometry,
        })
    return feature_collection(features, "Official Coimbatore ward boundaries"), len(features)


def grid_geojson(amenities: list[dict[str, Any]], columns: int = 56, rows: int = 44) -> tuple[dict[str, Any], float, float]:
    points = [local_xy(a["lon"], a["lat"]) for a in amenities]
    width = (BBOX["east"] - BBOX["west"]) / columns
    height = (BBOX["north"] - BBOX["south"]) / rows
    features = []
    within_400 = 0
    within_800 = 0
    total = columns * rows
    for row in range(rows):
        for col in range(columns):
            west = BBOX["west"] + col * width
            east = west + width
            north = BBOX["north"] - row * height
            south = north - height
            lon = (west + east) / 2
            lat = (south + north) / 2
            x, y = local_xy(lon, lat)
            distance = min(
                (math.hypot(x - px, y - py) for px, py in points),
                default=float("inf"),
            )
            if distance <= 400:
                within_400 += 1
            if distance <= 800:
                within_800 += 1
            if distance > 800:
                continue
            features.append({
                "type": "Feature",
                "properties": {
                    "nearest_m": round(distance, 1),
                    "band": "0–400 m" if distance <= 400 else "400–800 m",
                },
                "geometry": {
                    "type": "Polygon",
                    "coordinates": [[[west, south], [east, south], [east, north], [west, north], [west, south]]],
                },
            })
    return feature_collection(features, "Indicative proximity grid"), within_400 / total * 100, within_800 / total * 100


def main() -> None:
    PUBLIC.mkdir(exist_ok=True)
    amenities = read_amenities()
    roads, road_count = roads_geojson()
    wards, ward_count = wards_geojson()
    grid, within_400, within_800 = grid_geojson(amenities)
    (PUBLIC / "amenities.geojson").write_text(json.dumps(amenities_geojson(amenities), ensure_ascii=False), encoding="utf-8")
    (PUBLIC / "roads.geojson").write_text(json.dumps(roads, ensure_ascii=False), encoding="utf-8")
    (PUBLIC / "wards.geojson").write_text(json.dumps(wards, ensure_ascii=False), encoding="utf-8")
    (PUBLIC / "grid.geojson").write_text(json.dumps(grid, ensure_ascii=False), encoding="utf-8")
    metrics = {
        "snapshot": "2026-09-09",
        "bbox": BBOX,
        "amenities": len(amenities),
        "roads": road_count,
        "wards": ward_count,
        "boundary_source": "Official portal KML: required_map.kml",
        "within_400_pct": round(within_400, 2),
        "within_800_pct": round(within_800, 2),
        "categories": dict(Counter(item["category"] for item in amenities)),
    }
    (PUBLIC / "metrics.json").write_text(json.dumps(metrics, indent=2), encoding="utf-8")
    with (ROOT / "outputs" / "summary.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(["metric", "value", "interpretation"])
        writer.writerow(["mapped amenities", len(amenities), "deduplicated OSM public-facing records"])
        writer.writerow(["road context segments", road_count, "major roads plus sampled residential context"])
        writer.writerow(["official wards", ward_count, "official portal ward polygons"])
        writer.writerow(["grid within 400 m", f"{within_400:.2f}%", "regular grid cells near a mapped amenity"])
        writer.writerow(["grid within 800 m", f"{within_800:.2f}%", "regular grid cells near a mapped amenity"])
    print(f"Built {len(amenities):,} amenities, {road_count:,} road segments, {ward_count:,} official wards")
    print(f"Indicative grid proximity: {within_400:.1f}% within 400 m; {within_800:.1f}% within 800 m")


if __name__ == "__main__":
    main()
