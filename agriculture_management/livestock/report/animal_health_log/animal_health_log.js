// Copyright (c) 2025, aminos and contributors
// For license information, please see license.txt

frappe.query_reports["Animal Health Log"] = {
    "filters": [
        {
            "fieldname": "animal",
            "label": __("Animal"),
            "fieldtype": "Link",
            "options": "Animal"
        },
        {
            "fieldname": "livestock_group",
            "label": __("Livestock Group"),
            "fieldtype": "Link",
            "options": "Livestock Group"
        },
        {
            "fieldname": "date_range",
            "label": __("Date Range"),
            "fieldtype": "DateRange",
            "default": [frappe.datetime.add_months(frappe.datetime.get_today(), -1), frappe.datetime.get_today()]
        },
        // --- NEW FILTER ADDED HERE ---
        {
            "fieldname": "group_by",
            "label": __("Group By"),
            "fieldtype": "Select",
            "options": "\nEvent Date\nAnimal\nLivestock Group", // The user can choose one of these
            "default": "Event Date",
            "description": "Organize the report by the selected field."
        }
    ]
};