// map_defaults.js

// 1. Safely access the map defaults object.
// This function creates the object if it doesn't exist.
const map_settings = frappe.provide("frappe.utils.map_defaults");

// 2. Set the BASE layer to the ESRI satellite imagery.
// This is the beautiful photo background.
map_settings.tiles = "https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}";
map_settings.attribution = "Tiles &copy; Esri"; // A shorter attribution is fine here

// 3. Define the OVERLAY layer for labels, roads, and borders.
// We will use the free "Positron" labels from CARTO (formerly CartoDB).
const label_layer = {
    url: "https://{s}.basemaps.cartocdn.com/rastertiles/light_only_labels/{z}/{x}/{y}{r}.png",
    attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors &copy; <a href="https://carto.com/attributions">CARTO</a>'
};

// 4. Add the label layer to the map's default configuration.
// The Frappe framework has a special key, 'hybrid_layer', for this exact purpose.
// It will automatically overlay this on top of the base 'tiles' layer.
map_settings.hybrid_layer = label_layer;

// Optional: Set your preferred default center and zoom level.
map_settings.center = [34.85, 9.53]; // Centered on Tunisia
map_settings.zoom = 7;

console.log("Custom map defaults (with hybrid satellite and label layers) have been applied.");