// Copyright (c) 2025, aminos and contributors
/* eslint-disable */

frappe.query_reports["Nutrient & Chemical Consumption"] = {
	"filters": [
		{
			"fieldname": "date_range",
			"label": __("Period"),
			"fieldtype": "DateRange",
			"reqd": 1,
			"default": [frappe.datetime.add_months(frappe.datetime.get_today(), -1), frappe.datetime.get_today()]
		},
		{
			"fieldname": "item_group",
			"label": __("Filter by Item Group"),
			"fieldtype": "Link",
			"options": "Item Group",
			"description": __("Filter by 'Nutrients', 'Chemicals', etc.")
		},
		{
			"fieldname": "company",
			"label": __("Company"),
			"fieldtype": "Link",
			"options": "Company",
			"default": frappe.defaults.get_user_default("Company")
		}
	],
    
    // We are not generating a chart, so no get_chart_data function is needed.
};