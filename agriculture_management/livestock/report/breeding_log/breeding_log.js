// Copyright (c) 2025, aminos and contributors
// For license information, please see license.txt

frappe.query_reports["Breeding Log"] = {
    "filters": [
        {
            "fieldname": "dam",
            "label": __("Dam (Mother)"),
            "fieldtype": "Link",
            "options": "Animal",
            "get_query": () => ({ filters: { "gender": "Female" } })
        },
        {
            "fieldname": "sire",
            "label": __("Sire (Father)"),
            "fieldtype": "Link",
            "options": "Animal",
            "get_query": () => ({ filters: { "gender": "Male" } })
        },
        {
            "fieldname": "species",
            "label": __("Species"),
            "fieldtype": "Link",
            "options": "Livestock Species"
        },
        {
            "fieldname": "outcome",
            "label": __("Outcome"),
            "fieldtype": "Select",
            "options": "\nIn Progress\nSuccessful\nFailed\nMiscarriage/Aborted"
        },
        {
            "fieldname": "date_range",
            "label": __("Breeding Date Range"),
            "fieldtype": "DateRange",
            "default": [frappe.datetime.add_months(frappe.datetime.get_today(), -6), frappe.datetime.get_today()]
        }
    ]
};