app_name = "agriculture_management"
app_title = "Agriculture Management"
app_publisher = "aminos"
app_description = "Agriculture Management System"
app_email = "hamdiahmedamin@gmail.com"
app_license = "mit"
app_include_icons = "agriculture_management/icons.html"
app_include_css = "/assets/agriculture_management/css/vis-network.css"
required_apps = ["erpnext"]

app_include_js = [
    "https://unpkg.com/leaflet-bing-layer/leaflet-bing-layer.js",
    "/assets/agriculture_management/js/map_defaults.js",
    "/assets/agriculture_management/js/snap.svg-min.js",
    "/assets/agriculture_management/js/ternary_plot.js",
    "/assets/agriculture_management/js/utils.js",
    "/assets/agriculture_management/js/all.min.js",
]
# Installation
# ------------

# before_install = "agriculture_management.install.before_install"
after_install = "agriculture_management.install.after_install"
after_sync = "agriculture_management.install.after_sync"
doctype_js = {
    "Asset": "public/js/asset.js"
}
# Uninstallation
# ------------

before_uninstall = "agriculture_management.uninstall.before_uninstall"

doc_events = {
    "Animal": {
        "on_update": "agriculture_management.livestock.api.handle_livestock_status_change"
    },
    "Sales Invoice": {
        "on_submit": "agriculture_management.livestock.api.update_livestock_status_on_sale"
    },
    "Stock Entry": {
        "on_submit": "agriculture_management.livestock.api.sync_livestock_location_on_move",
        "on_cancel": "agriculture_management.livestock.utils.revert_feeding_on_se_cancel"
    },
    "Delivery Note": {
        "on_cancel": "agriculture_management.livestock.utils.update_flock_on_dn_cancel",
        "validate": "agriculture_management.livestock.utils.validate_delivery_of_livestock"
    }
}

scheduler_events = {
    "cron": {
        "*/5 * * * *": [  # This means "run every 5 minutes"
            "agriculture_management.livestock.tasks.process_device_logs"
        ]},
    "daily": [
        "agriculture_management.livestock.tasks.check_for_due_health_events",
        "agriculture_management.livestock.tasks.check_for_pasture_moves",
        "agriculture_management.livestock.tasks.check_withdrawal_periods",
        "agriculture_management.livestock.utils.check_and_update_withdrawal_status"
    ]
}

fixtures = [
    "Custom Field",
    "Property Setter",
    "Server Script",
    "Client Script"
]
# auth_hooks = [
# "agriculture_management.auth.validate"
# ]
# fixtures = ["Custom Field"]
global_search_doctypes = {
    "Agriculture Management": [
        {'doctype': 'Weather', 'index': 1},
        {'doctype': 'Soil Texture', 'index': 2},
        {'doctype': 'Water Analysis', 'index': 3},
        {'doctype': 'Soil Analysis', 'index': 4},
        {'doctype': 'Plant Analysis', 'index': 5},
        {'doctype': 'Agriculture Analysis Criteria', 'index': 6},
        {'doctype': 'Disease', 'index': 7},
        {'doctype': 'Crop', 'index': 8},
        {'doctype': 'Fertilizer', 'index': 9},
        {'doctype': 'Crop Cycle', 'index': 10}
    ]
}
