const COLORS = {
  health: "#e05b5c",
  education: "#3979a8",
  civic: "#7454a0",
  community: "#1e9b9b",
  recreation: "#5f9e76",
  mobility: "#d4862d",
  other: "#7e8b8f",
};

const LABELS = {
  health: "Health",
  education: "Education",
  civic: "Civic & safety",
  community: "Community",
  recreation: "Recreation",
  mobility: "Mobility",
  other: "Other",
};

const map = L.map("map", {
  preferCanvas: true,
  zoomControl: false,
  minZoom: 10,
  maxZoom: 18,
}).setView([11.0018, 76.9628], 11);

L.control.zoom({ position: "topright" }).addTo(map);

const basemap = L.tileLayer("https://tile.openstreetmap.org/{z}/{x}/{y}.png", {
  maxZoom: 19,
  attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
}).addTo(map);

const markerIndex = new Map();
let amenities;
let metrics;
let categoryLayers = {};
let roadsLayer;
let gridLayer;
let wardsLayer;

const setText = (id, value) => {
  const element = document.getElementById(id);
  if (element) element.textContent = value;
};

function amenityColor(category) {
  return COLORS[category] || COLORS.other;
}

function amenityPopup(properties) {
  const name = escapeHtml(properties.name || "Unnamed mapped amenity");
  const kind = escapeHtml(properties.kind || "public amenity");
  const category = escapeHtml(LABELS[properties.category] || "Other");
  return '<div class="amenity-popup"><h3>' + name + '</h3><p>' + category + ' · ' + kind + '</p></div>';
}

function escapeHtml(value) {
  return String(value).replace(/[&<>"']/g, (char) => ({
    "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#039;",
  }[char]));
}

function pointLayerForCategory(category) {
  return L.geoJSON(amenities, {
    filter: (feature) => feature.properties.category === category,
    pointToLayer: (feature, latlng) => {
      const marker = L.circleMarker(latlng, {
        radius: 5,
        color: "#fff",
        weight: 1.2,
        fillColor: amenityColor(category),
        fillOpacity: 0.9,
      });
      const properties = feature.properties;
      marker.bindPopup(amenityPopup(properties), { maxWidth: 260 });
      marker.bindTooltip(escapeHtml(properties.name || properties.kind || "Mapped amenity"), {
        direction: "top",
        offset: [0, -5],
      });
      markerIndex.set(properties.osm_id || properties.name + latlng.toString(), marker);
      return marker;
    },
  });
}

function renderMetrics() {
  setText("hero-800", Number(metrics.within_800_pct).toFixed(1) + "%");
  setText("stat-amenities", Number(metrics.amenities).toLocaleString());
  setText("stat-wards", Number(metrics.wards).toLocaleString());
  setText("stat-roads", Number(metrics.roads).toLocaleString());
  setText("stat-400", Number(metrics.within_400_pct).toFixed(1) + "%");
  setText("stat-800", Number(metrics.within_800_pct).toFixed(1) + "%");
  setText("snapshot", metrics.snapshot);
}

function renderCategorySummary() {
  const counts = metrics.categories;
  const maximum = Math.max(...Object.values(counts));
  const container = document.getElementById("category-summary");
  container.innerHTML = Object.entries(LABELS)
    .filter(([key]) => counts[key])
    .map(([key, label]) => {
      const width = (counts[key] / maximum) * 100;
      return '<div class="category-row"><span>' + label + '</span><div class="bar"><i style="width:' + width.toFixed(1) + '%;background:' + COLORS[key] + '"></i></div><b>' + counts[key] + '</b></div>';
    }).join("");
}

function renderCategoryFilters() {
  const container = document.getElementById("category-filters");
  container.innerHTML = Object.entries(LABELS)
    .filter(([key]) => metrics.categories[key])
    .map(([key, label]) => '<label class="category-filter"><input type="checkbox" data-category="' + key + '" checked><span class="swatch" style="background:' + COLORS[key] + '"></span><span>' + label + '</span><b>' + metrics.categories[key] + '</b></label>')
    .join("");
  container.querySelectorAll("[data-category]").forEach((input) => {
    input.addEventListener("change", () => {
      const layer = categoryLayers[input.dataset.category];
      if (input.checked) map.addLayer(layer);
      else map.removeLayer(layer);
    });
  });
}

function setupLayers() {
  gridLayer = L.geoJSON(window.__GRID_DATA__, {
    style: (feature) => ({
      color: "#fff",
      weight: 0.35,
      fillColor: feature.properties.nearest_m <= 400 ? "#238b8d" : "#78c2ad",
      fillOpacity: feature.properties.nearest_m <= 400 ? 0.38 : 0.24,
    }),
    onEachFeature: (feature, layer) => {
      layer.bindTooltip(feature.properties.band + " · nearest mapped amenity: " + feature.properties.nearest_m + " m");
    },
  }).addTo(map);

  roadsLayer = L.geoJSON(window.__ROADS_DATA__, {
    style: (feature) => {
      const highway = feature.properties.highway;
      const styles = {
        motorway: ["#c55a59", 3],
        trunk: ["#cd6c51", 2.5],
        primary: ["#d49a58", 2],
        secondary: ["#94aaa6", 1.45],
        tertiary: ["#b0c2bd", 1],
      };
      const style = styles[highway] || ["#c9d4d0", 0.6];
      return { color: style[0], weight: style[1], opacity: 0.75 };
    },
  }).addTo(map);

  wardsLayer = L.geoJSON(window.__WARDS_DATA__, {
    style: {
      color: "#17212b",
      weight: 1.3,
      opacity: 0.62,
      dashArray: "5 4",
      fillColor: "#ffffff",
      fillOpacity: 0.025,
    },
    onEachFeature: (feature, layer) => {
      const p = feature.properties;
      const ward = escapeHtml(p.ward_lgd_name || p.sourcewardcode || "Unknown");
      const zone = escapeHtml(p.zone || "Coimbatore");
      layer.bindTooltip("Ward " + ward + " · " + zone, { sticky: true });
      layer.bindPopup('<div class="amenity-popup"><h3>Ward ' + ward + '</h3><p>' + zone + ' · official portal boundary</p></div>');
    },
  }).addTo(map);

  Object.keys(LABELS).forEach((category) => {
    categoryLayers[category] = pointLayerForCategory(category).addTo(map);
  });

  L.control.layers(
    { "OpenStreetMap": basemap },
    { "Proximity grid": gridLayer, "Official wards": wardsLayer, "Road context": roadsLayer },
    { collapsed: false, position: "topright" },
  ).addTo(map);

  map.fitBounds([[10.90, 76.82], [11.12, 77.10]], { padding: [20, 20] });
}

function searchAmenity(event) {
  event.preventDefault();
  const query = document.getElementById("search-input").value.trim().toLowerCase();
  const status = document.getElementById("search-status");
  if (!query) {
    status.textContent = "Enter a name, category or amenity type.";
    return;
  }
  const feature = amenities.features.find((item) => {
    const p = item.properties;
    return [p.name, p.kind, p.category].join(" ").toLowerCase().includes(query);
  });
  if (!feature) {
    status.textContent = "No mapped match found.";
    return;
  }
  const p = feature.properties;
  const coords = feature.geometry.coordinates;
  const marker = markerIndex.get(p.osm_id || p.name + L.latLng(coords[1], coords[0]).toString());
  const filter = document.querySelector('[data-category="' + p.category + '"]');
  if (filter && !filter.checked) {
    filter.checked = true;
    map.addLayer(categoryLayers[p.category]);
  }
  map.setView([coords[1], coords[0]], 15, { animate: true });
  if (marker) marker.openPopup();
  status.textContent = p.name || p.kind || "Mapped amenity";
}

function downloadCsv() {
  const rows = [["name", "category", "type", "longitude", "latitude"]];
  amenities.features.forEach((feature) => {
    const p = feature.properties;
    const [lon, lat] = feature.geometry.coordinates;
    rows.push([p.name, p.category, p.kind, lon, lat]);
  });
  const csv = rows.map((row) => row.map((value) => '"' + String(value ?? "").replaceAll('"', '""') + '"').join(",")).join("\n");
  const url = URL.createObjectURL(new Blob([csv], { type: "text/csv;charset=utf-8" }));
  const link = document.createElement("a");
  link.href = url;
  link.download = "coimbatore_mapped_amenities.csv";
  link.click();
  URL.revokeObjectURL(url);
}

async function loadData() {
  const status = document.getElementById("load-status");
  try {
    const responses = await Promise.all([
      fetch("./data/amenities.geojson"),
      fetch("./data/roads.geojson"),
      fetch("./data/grid.geojson"),
      fetch("./data/wards.geojson"),
      fetch("./data/metrics.json"),
    ]);
    if (responses.some((response) => !response.ok)) throw new Error("A local data asset could not be loaded.");
    [amenities, window.__ROADS_DATA__, window.__GRID_DATA__, window.__WARDS_DATA__, metrics] = await Promise.all(responses.map((response) => response.json()));
    renderMetrics();
    renderCategorySummary();
    renderCategoryFilters();
    setupLayers();
    document.getElementById("toggle-grid").addEventListener("change", (event) => event.target.checked ? map.addLayer(gridLayer) : map.removeLayer(gridLayer));
    document.getElementById("toggle-wards").addEventListener("change", (event) => event.target.checked ? map.addLayer(wardsLayer) : map.removeLayer(wardsLayer));
    document.getElementById("toggle-roads").addEventListener("change", (event) => event.target.checked ? map.addLayer(roadsLayer) : map.removeLayer(roadsLayer));
    document.getElementById("search-form").addEventListener("submit", searchAmenity);
    document.getElementById("download-csv").addEventListener("click", downloadCsv);
    status.textContent = "Ready · " + Number(metrics.amenities).toLocaleString() + " mapped amenities";
  } catch (error) {
    status.textContent = "Map data failed to load. Serve this folder with a local web server.";
    status.classList.add("error");
    console.error(error);
  }
}

loadData();
