// Copyright (c) 2025, aminos and contributors
// For license information, please see license.txt

frappe.query_reports["Livestock Movement Log"] = {
    "filters": [
        {
            "fieldname": "movement_date",
            "label": __("Movement Date Range"),
            "fieldtype": "DateRange",
            "default": [frappe.datetime.add_months(frappe.datetime.get_today(), -1), frappe.datetime.get_today()]
        },
        {
            "fieldname": "animal",
            "label": __("Specific Animal"),
            "fieldtype": "Link",
            "options": "Animal"
        },
        {
            "fieldname": "livestock_group",
            "label": __("Specific Group"),
            "fieldtype": "Link",
            "options": "Livestock Group"
        },
        {
            "fieldname": "from_location",
            "label": __("From Location"),
            "fieldtype": "Link",
            "options": "Warehouse"
        },
        {
            "fieldname": "to_location",
            "label": __("To Location"),
            "fieldtype": "Link",
            "options": "Warehouse"
        },
        {
            "fieldname": "reason",
            "label": __("Reason"),
            "fieldtype": "Select",
            "options": "\nPasture Rotation\nQuarantine\nSale Preparation\nWeaning\nHealth Isolation"
        }
    ]
};