# /// script
# requires-python = ">=3.12"
# dependencies = ["numpy", "pillow", "shapely"]
# ///
"""Builds the night map of Galicia that the web app draws on its globe.

Run it only to refresh the data; the results are versioned:

    uv run scripts/galicia_map.py

Sources, downloaded from pinned or stable URLs and cached in ~/.cache/karaoke/galicia:

- Boundary: Natural Earth admin-1 at 1:10m (public domain), the four provinces merged. It
  decides what is Galicia and what is Asturias, León, Zamora or Portugal.
- Relief and coast: Mapzen Terrain Tiles on AWS Open Data (SRTM and EU-DEM on land, ETOPO1 at
  sea), zoom 9, about 220 m per pixel. Inside the boundary, and up to a few kilometres off it
  for the islands, whatever stands above the sea is land: the rías and the islands come out of
  the relief itself, finer than the boundary's coast.
- Lights: Kontur Population 2023, people per 400 m H3 hexagon (CC BY 4.0, via HDX). Every
  inhabited cell inside Galicia becomes one light, brighter with more people.
- Lighthouses: Wikidata (CC0): position, the light's character as charts write it ("Fl(4) W
  20s": four flashes every twenty seconds) and its range in nautical miles.

Galicia is drawn on the front of a small planet, much bigger than it would be on the real
Earth: local flat coordinates around its centre become angles on the sphere (`theta` east,
`phi` north; the widest side spans `SPAN_DEGREES` each way), so a point is
(cos phi * sin theta, sin phi, cos phi * cos theta) in units of the sphere's radius.

Outputs (web/src/lib/globe/):

- `galicia.ts`: the projection's constants, the outline as an SVG path for the still drawing
  (orthographic, viewBox -1000..1000), cities, lighthouses and totals.
- `galicia-map.bin`: a gzip-compressed raster (named .bin so no server labels it as
  gzip-encoded and has the browser unzip it on the way: the page unzips it itself) on a `GRID`
  by `GRID` grid, uniform in theta and phi over ±`EXTENT`, cropped to Galicia: little-endian
  uint16 grid, column, row, width, height; then width * height uint8 heights in rows from the
  north (0 sea; otherwise 1 + 254 * sqrt(metres / HEIGHT_MAX)); then width * height uint8
  lights (0 dark; otherwise the log of the people, 1..255); then width * height uint8
  provinces (0 none; 1 A Coruña, 2 Lugo, 3 Ourense, 4 Pontevedra), for the lines between them.
  A cell is about 0.45 km.
"""

import gzip
import json
import math
import re
import sqlite3
import struct
import sys
import urllib.parse
import urllib.request
from pathlib import Path

import numpy as np
from PIL import Image
from shapely import contains_xy
from shapely.geometry import shape
from shapely.ops import unary_union

NATURAL_EARTH = (
    "https://raw.githubusercontent.com/nvkelso/natural-earth-vector/"
    "ca96624a56bd078437bca8184e78163e5039ad19/geojson/ne_10m_admin_1_states_provinces.geojson"
)
KONTUR = (
    "https://geodata-eu-central-1-kontur-public.s3.amazonaws.com/kontur_datasets/"
    "kontur_population_ES_20231101.gpkg.gz"
)
TERRAIN = "https://s3.amazonaws.com/elevation-tiles-prod/terrarium/{z}/{x}/{y}.png"
TERRAIN_ZOOM = 9
WIKIDATA = "https://query.wikidata.org/sparql"
# Lighthouses (Q39715 and its subclasses) inside a box around Galicia; the boundary filters it.
LIGHTHOUSES_QUERY = """
SELECT ?item ?name ?coord ?character ?range WHERE {
  ?item wdt:P31/wdt:P279* wd:Q39715 .
  SERVICE wikibase:box {
    ?item wdt:P625 ?coord .
    bd:serviceParam wikibase:cornerSouthWest "Point(-9.6 41.7)"^^geo:wktLiteral .
    bd:serviceParam wikibase:cornerNorthEast "Point(-6.9 43.9)"^^geo:wktLiteral .
  }
  OPTIONAL { ?item wdt:P1030 ?character }
  OPTIONAL { ?item wdt:P2929 ?range }
  OPTIONAL { ?item rdfs:label ?gl FILTER(LANG(?gl) = "gl") }
  OPTIONAL { ?item rdfs:label ?es FILTER(LANG(?es) = "es") }
  BIND(COALESCE(?gl, ?es) AS ?name)
}
"""
USER_AGENT = "galicia-night-map-builder/1.0 (data script)"
CACHE = Path.home() / ".cache/karaoke/galicia"
OUT = Path(__file__).resolve().parents[1] / "web/src/lib/globe"

SPAN_DEGREES = 34.0
# The grid reaches a little past Galicia's widest side, for the islands and the capes.
MARGIN = 1.06
GRID = 512
HEIGHT_MAX = 2200.0
# How far off the boundary land still counts (islands, capes the 1:10m coast cuts): ~6 km.
SEAWARD = 0.06
# Douglas-Peucker tolerance of the still outline, in degrees (~250 m).
OUTLINE_TOLERANCE = 0.0025
EARTH_RADIUS = 6378137.0
BOX = (-9.6, 41.6, -6.5, 44.0)

CITIES = [
    ("A Coruña", -8.4115, 43.3623),
    ("Ferrol", -8.2326, 43.4832),
    ("Santiago", -8.5448, 42.8782),
    ("Lugo", -7.5560, 43.0097),
    ("Pontevedra", -8.6446, 42.4310),
    ("Ourense", -7.8648, 42.3358),
    ("Vigo", -8.7207, 42.2406),
]
# As Natural Earth names them, in the order the raster numbers them from 1.
PROVINCES = ["La Coruña", "Lugo", "Orense", "Pontevedra"]
# People counted around a city: within this many kilometres of its centre.
CITY_RADIUS_KM = 5.0


def _fetch(url: str) -> bytes:
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})  # noqa: S310
    with urllib.request.urlopen(request, timeout=300) as response:  # noqa: S310 - fixed https URL
        data: bytes = response.read()
        return data


def _cached(url: str, name: str) -> Path:
    path = CACHE / name
    path.parent.mkdir(parents=True, exist_ok=True)
    if not path.exists():
        print(f"downloading {url}", file=sys.stderr)
        path.write_bytes(_fetch(url))
    return path


def boundaries():  # type: ignore[no-untyped-def]
    """Galicia, and everything else on land around it (the neighbours)."""
    data = json.loads(_cached(NATURAL_EARTH, "ne_10m_admin_1.geojson").read_text())
    galicia: dict[str, object] = {}
    others = []
    box = shape(
        {
            "type": "Polygon",
            "coordinates": [
                [
                    (BOX[0], BOX[1]),
                    (BOX[2], BOX[1]),
                    (BOX[2], BOX[3]),
                    (BOX[0], BOX[3]),
                    (BOX[0], BOX[1]),
                ]
            ],
        }
    )
    for feature in data["features"]:
        properties = feature["properties"]
        geometry = shape(feature["geometry"])
        if properties.get("region") == "Galicia" and properties.get("iso_a2") == "ES":
            galicia[properties["name"]] = geometry
        elif geometry.intersects(box):
            others.append(geometry.intersection(box))
    if sorted(galicia) != sorted(PROVINCES):
        raise SystemExit(f"expected the four provinces of Galicia, found {sorted(galicia)}")
    provinces = [galicia[name] for name in PROVINCES]
    return unary_union(provinces), unary_union(others), provinces


def hexagons() -> np.ndarray:
    """(lon, lat, people) of every hexagon of Spain, from the GeoPackage's bounding boxes."""
    packed = _cached(KONTUR, "kontur_population_ES_20231101.gpkg.gz")
    gpkg = CACHE / "kontur_population_ES_20231101.gpkg"
    if not gpkg.exists():
        gpkg.write_bytes(gzip.decompress(packed.read_bytes()))
    rows = []
    with sqlite3.connect(gpkg) as db:
        for blob, people in db.execute("select geom, population from population"):
            # GeoPackage header: 'GP', version, flags (bit 0 little endian, bits 1-3 envelope).
            flags = blob[3]
            if (flags >> 1) & 7 != 1:
                raise SystemExit("expected an xy envelope in every geometry")
            order = "<" if flags & 1 else ">"
            min_x, max_x, min_y, max_y = struct.unpack(order + "4d", blob[8:40])
            x, y = (min_x + max_x) / 2, (min_y + max_y) / 2  # Web Mercator metres
            lon = math.degrees(x / EARTH_RADIUS)
            lat = math.degrees(2 * math.atan(math.exp(y / EARTH_RADIUS)) - math.pi / 2)
            rows.append((lon, lat, people))
    return np.array(rows, dtype=np.float64)


class Relief:
    """Metres above the sea anywhere in the box, from the terrain tiles."""

    def __init__(self) -> None:
        n = 2**TERRAIN_ZOOM
        self.n = n
        self.x0 = int((BOX[0] + 180) / 360 * n)
        self.x1 = int((BOX[2] + 180) / 360 * n)
        self.y0 = int(self._row(BOX[3]))
        self.y1 = int(self._row(BOX[1]))
        tiles = []
        for y in range(self.y0, self.y1 + 1):
            strip = []
            for x in range(self.x0, self.x1 + 1):
                url = TERRAIN.format(z=TERRAIN_ZOOM, x=x, y=y)
                path = _cached(url, f"dem/{TERRAIN_ZOOM}-{x}-{y}.png")
                rgb = np.asarray(Image.open(path).convert("RGB"), dtype=np.float64)
                strip.append(rgb[:, :, 0] * 256 + rgb[:, :, 1] + rgb[:, :, 2] / 256 - 32768)
            tiles.append(np.hstack(strip))
        self.metres = np.vstack(tiles)

    def _row(self, lat: float | np.ndarray) -> float | np.ndarray:
        return (1 - np.arcsinh(np.tan(np.radians(lat))) / math.pi) / 2 * self.n

    def __call__(self, lon: np.ndarray, lat: np.ndarray) -> np.ndarray:
        """Bilinear sample at each point."""
        px = ((lon + 180) / 360 * self.n - self.x0) * 256 - 0.5
        py = (np.asarray(self._row(lat)) - self.y0) * 256 - 0.5
        height, width = self.metres.shape
        px = np.clip(px, 0, width - 1.001)
        py = np.clip(py, 0, height - 1.001)
        ix, iy = px.astype(int), py.astype(int)
        fx, fy = px - ix, py - iy
        m = self.metres
        top = m[iy, ix] * (1 - fx) + m[iy, ix + 1] * fx
        bottom = m[iy + 1, ix] * (1 - fx) + m[iy + 1, ix + 1] * fx
        return np.asarray(top * (1 - fy) + bottom * fy)


class Projection:
    """Galicia's local coordinates as angles on the front of the sphere."""

    def __init__(self, region) -> None:  # type: ignore[no-untyped-def]
        centre = region.centroid
        self.lon0, self.lat0 = centre.x, centre.y
        self.cos0 = math.cos(math.radians(self.lat0))
        min_lon, min_lat, max_lon, max_lat = region.bounds
        half = max((max_lon - min_lon) * self.cos0, max_lat - min_lat) / 2
        self.scale = math.radians(SPAN_DEGREES) / half
        self.extent = math.radians(SPAN_DEGREES) * MARGIN
        # Kilometres on the ground per radian on the sphere.
        self.km = math.radians(1) * EARTH_RADIUS / 1000 / self.scale

    def angles(self, lon: np.ndarray, lat: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
        theta = (np.asarray(lon) - self.lon0) * self.cos0 * self.scale
        phi = (np.asarray(lat) - self.lat0) * self.scale
        return theta, phi

    def lonlat(self, theta: np.ndarray, phi: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
        return self.lon0 + theta / (self.cos0 * self.scale), self.lat0 + phi / self.scale

    def flat(self, lon: np.ndarray, lat: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
        """Orthographic x, y (+y up) for the still drawing."""
        theta, phi = self.angles(lon, lat)
        return np.cos(phi) * np.sin(theta), np.sin(phi)

    def cell(self, theta: np.ndarray, phi: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
        column = np.floor((theta + self.extent) / (2 * self.extent) * GRID).astype(int)
        row = np.floor((self.extent - phi) / (2 * self.extent) * GRID).astype(int)
        return column, row


def _path(project: Projection, region) -> str:  # type: ignore[no-untyped-def]
    simple = region.simplify(OUTLINE_TOLERANCE, preserve_topology=True)
    polygons = sorted(getattr(simple, "geoms", [simple]), key=lambda p: -p.area)
    parts = []
    for polygon in polygons:
        lon, lat = np.array(polygon.exterior.coords).T
        x, y = project.flat(lon, lat)
        points = [f"{px * 1000:.1f} {-py * 1000:.1f}" for px, py in zip(x, y, strict=True)]
        parts.append("M" + "L".join(points[:-1]) + "Z")
    return "".join(parts)


CHARACTER = re.compile(
    r"^\s*(?P<kind>LFl|Fl|Oc|Iso|VQ|Q)\s*(?:\(\s*(?P<group>\d+)(?:\s*\+\s*(?P<plus>\d+))?\s*\))?"
    r"[^0-9]*?(?P<period>\d+(?:[.,]\d+)?)\s*s\b"
)


def character(text: str) -> dict[str, object] | None:
    """The rhythm of a light as charts write it: "Fl(4) W 20s", "Oc W 8s", "Fl (3+1) W 24s"."""
    match = CHARACTER.match(text)
    if match is None:
        return None
    flashes = int(match["group"] or 1) + int(match["plus"] or 0)
    return {
        "kind": match["kind"],
        "flashes": flashes,
        "period": float(match["period"].replace(",", ".")),
    }


def lighthouses(region) -> list[dict[str, object]]:  # type: ignore[no-untyped-def]
    path = CACHE / "lighthouses.json"
    if not path.exists():
        url = (
            WIKIDATA + "?" + urllib.parse.urlencode({"query": LIGHTHOUSES_QUERY, "format": "json"})
        )
        print("downloading the lighthouses from Wikidata", file=sys.stderr)
        path.write_bytes(_fetch(url))
    rows = json.loads(path.read_text())["results"]["bindings"]
    near = region.buffer(SEAWARD)
    found: dict[str, dict[str, object]] = {}
    for row in rows:
        point = re.match(r"Point\(([-\d.]+) ([-\d.]+)\)", row["coord"]["value"])
        if point is None or "name" not in row:
            continue
        lon, lat = float(point[1]), float(point[2])
        if not contains_xy(near, lon, lat):
            continue
        name = row["name"]["value"]
        name = name[0].upper() + name[1:]
        light = found.setdefault(row["item"]["value"], {"name": name, "lon": lon, "lat": lat})
        rhythm = character(row["character"]["value"]) if "character" in row else None
        if rhythm is not None:
            light.update(rhythm)
        if "range" in row:
            miles = float(row["range"]["value"])
            light["range"] = max(miles, float(light.get("range", 0)))  # type: ignore[arg-type]
    return sorted(found.values(), key=lambda light: (-float(light["lat"]), float(light["lon"])))  # type: ignore[arg-type]


def main() -> None:
    region, neighbours, provinces = boundaries()
    project = Projection(region)
    relief = Relief()

    # The grid, uniform in angle; every cell's centre back on the ground.
    step = 2 * project.extent / GRID
    theta = -project.extent + (np.arange(GRID) + 0.5) * step
    phi = project.extent - (np.arange(GRID) + 0.5) * step
    theta_grid, phi_grid = np.meshgrid(theta, phi)
    lon, lat = project.lonlat(theta_grid, phi_grid)
    metres = relief(lon.ravel(), lat.ravel()).reshape(GRID, GRID)
    inside = contains_xy(region, lon.ravel(), lat.ravel()).reshape(GRID, GRID)
    offshore = contains_xy(region.buffer(SEAWARD), lon.ravel(), lat.ravel()).reshape(GRID, GRID)
    foreign = contains_xy(neighbours.buffer(0.004), lon.ravel(), lat.ravel()).reshape(GRID, GRID)
    land = (metres > 0.5) & (inside | (offshore & ~foreign))
    height = np.where(
        land, 1 + np.round(254 * np.sqrt(np.clip(metres, 0, HEIGHT_MAX) / HEIGHT_MAX)), 0
    )

    province = np.zeros((GRID, GRID))
    for number, shape_ in enumerate(provinces, start=1):
        here = contains_xy(shape_, lon.ravel(), lat.ravel()).reshape(GRID, GRID)
        province[here & land] = number

    cells = hexagons()
    near = (
        (cells[:, 0] > BOX[0])
        & (cells[:, 0] < BOX[2])
        & (cells[:, 1] > BOX[1])
        & (cells[:, 1] < BOX[3])
    )
    cells = cells[near]
    # A little margin keeps the coastal villages that the 1:10m coast cuts off.
    in_galicia = contains_xy(region.buffer(0.01), cells[:, 0], cells[:, 1])
    cells = cells[in_galicia & (cells[:, 2] > 0)]
    people = cells[:, 2]
    column, row = project.cell(*project.angles(cells[:, 0], cells[:, 1]))
    grid = np.zeros(GRID * GRID)
    np.add.at(grid, np.clip(row, 0, GRID - 1) * GRID + np.clip(column, 0, GRID - 1), people)
    grid = grid.reshape(GRID, GRID)
    light = np.where(
        grid > 0, np.clip(np.round(np.log1p(grid) / np.log1p(grid.max()) * 255), 1, 255), 0
    )

    rows, columns = np.nonzero((height > 0) | (light > 0))
    top, left = int(rows.min()), int(columns.min())
    bottom, right = int(rows.max()) + 1, int(columns.max()) + 1
    width, tall = right - left, bottom - top
    header = struct.pack("<5H", GRID, left, top, width, tall)
    raster = (
        header
        + height[top:bottom, left:right].astype("u1").tobytes()
        + light[top:bottom, left:right].astype("u1").tobytes()
        + province[top:bottom, left:right].astype("u1").tobytes()
    )
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "galicia-map.bin").write_bytes(gzip.compress(raster, compresslevel=9, mtime=0))

    cities = []
    for name, city_lon, city_lat in CITIES:
        t, p = project.angles(np.array([city_lon]), np.array([city_lat]))
        x, y = project.flat(np.array([city_lon]), np.array([city_lat]))
        east = (cells[:, 0] - city_lon) * math.cos(math.radians(city_lat)) * 111.32
        north = (cells[:, 1] - city_lat) * 110.57
        around = people[np.hypot(east, north) < CITY_RADIUS_KM].sum()
        cities.append(
            {
                "name": name,
                "theta": round(float(t[0]), 4),
                "phi": round(float(p[0]), 4),
                "x": round(float(x[0]), 4),
                "y": round(float(y[0]), 4),
                "people": int(round(float(around), -2)),
            }
        )

    beacons = []
    for found in lighthouses(region):
        t, p = project.angles(np.array([found["lon"]]), np.array([found["lat"]]))
        beacon: dict[str, object] = {
            "name": found["name"],
            "theta": round(float(t[0]), 4),
            "phi": round(float(p[0]), 4),
        }
        for key in ("kind", "flashes", "period", "range"):
            if key in found:
                beacon[key] = found[key]
        beacons.append(beacon)

    lights = int((light > 0).sum())
    module = f"""/*
 * Generated by scripts/galicia_map.py. Do not edit by hand.
 * Boundary: Natural Earth (public domain). Relief: Mapzen Terrain Tiles (SRTM, EU-DEM, ETOPO1).
 * Lights: Kontur Population 2023 (CC BY 4.0). Lighthouses: Wikidata (CC0).
 */

/** The raster reaches this many radians each way from Galicia's centre, east and north. */
export const EXTENT = {project.extent:.6f};
/** Kilometres on the ground per radian on the globe. */
export const KM_PER_RADIAN = {project.km:.3f};
/** Metres of the tallest height the raster can hold. */
export const HEIGHT_MAX = {HEIGHT_MAX:.0f};

/** Outline of Galicia for the still drawing, in an SVG viewBox of -1000 -1000 2000 2000. */
export const OUTLINE = '{_path(project, region)}';

export interface City {{
	name: string;
	/** Angles on the globe from Galicia's centre, in radians: east and north. */
	theta: number;
	phi: number;
	/** The same place on the still drawing, in units of the sphere's radius (+y up). */
	x: number;
	y: number;
	/** People living within {CITY_RADIUS_KM:.0f} km of its centre. */
	people: number;
}}

export const CITIES: readonly City[] = {json.dumps(cities, ensure_ascii=False)};

export interface Lighthouse {{
	name: string;
	theta: number;
	phi: number;
	/** Its light as charts write it: Fl flashing, Oc occulting, Iso equal light and dark. */
	kind?: 'Fl' | 'LFl' | 'Oc' | 'Iso' | 'Q' | 'VQ';
	/** Flashes in each period, and the period in seconds. */
	flashes?: number;
	period?: number;
	/** How far it is seen, in nautical miles. */
	range?: number;
}}

/** The lighthouses of the Galician coast, from the north-east round to the south. */
export const LIGHTHOUSES: readonly Lighthouse[] = {json.dumps(beacons, ensure_ascii=False)};

/** People counted inside Galicia and the lights they make (inhabited cells of about 0.45 km). */
export const PEOPLE = {int(people.sum())};
export const LIGHTS = {lights};
"""
    (OUT / "galicia.ts").write_text(module)
    size = (OUT / "galicia-map.bin").stat().st_size
    print(
        f"{int(land.sum())} land cells, {lights} lights, {int(people.sum())} people, "
        f"{len(beacons)} lighthouses, {size / 1024:.0f} kB",
        file=sys.stderr,
    )


if __name__ == "__main__":
    main()
