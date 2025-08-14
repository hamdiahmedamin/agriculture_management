// Copyright (c) 2025, aminos and contributors
// For license information, please see license.txt

frappe.query_reports["Livestock Valuation"] = {
    "filters": [
        {
            "fieldname": "as_on_date",
            "label": __("As on Date"),
            "fieldtype": "Date",
            "default": frappe.datetime.now_date(),
            "reqd": 1
        },
        {
            "fieldname": "livestock_group",
            "label": __("Livestock Group"),
            "fieldtype": "Link",
            "options": "Livestock Group"
        },
        {
            "fieldname": "valuation_method",
            "label": __("Valuation Method"),
            "fieldtype": "Select",
            "options": [
                "Acquisition Cost",
                "Standard Cost",
                "Last Purchase Price"
            ],
            "default": "Acquisition Cost",
            "reqd": 1
        }
    ]
};