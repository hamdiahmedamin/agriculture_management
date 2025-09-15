// Copyright (c) 2025, aminos and contributors
// For license information, please see license.txt
// Copyright (c) 2025, aminos and contributors
/* eslint-disable */

frappe.query_reports["Maintenance & Compliance Schedule"] = {
	"filters": [
		{
			"fieldname": "date_range",
			"label": __("Date Range"),
			"fieldtype": "DateRange",
			"description": __("Filters tasks due or completed in this period")
		},
		{
			"fieldname": "hydroponic_system",
			"label": __("Hydroponic System"),
			"fieldtype": "Link",
			"options": "Asset",
			"get_query": function() {
				return {
					filters: { 
						"asset_category": ["in", ["Hydroponic Systems", "Hydroponic Equipments"]],
						"status": ["!=", "Cancelled"] 
					}
				};
			}
		},
		{
			"fieldname": "status",
			"label": __("Status"),
			"fieldtype": "Select",
			"options": [
				"",
				"Upcoming",
				"Overdue",
				"Completed"
			],
			"default": "Upcoming"
		}
	]
};