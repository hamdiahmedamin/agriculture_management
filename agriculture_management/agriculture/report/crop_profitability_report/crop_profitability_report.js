// Copyright (c) 2025, aminos and contributors
/* eslint-disable */

frappe.query_reports["Crop Profitability Report"] = {
	"filters": [
		{
			"fieldname": "date_range",
			"label": __("Harvest Period"),
			"fieldtype": "DateRange",
			"reqd": 1,
			"default": [frappe.datetime.add_months(frappe.datetime.get_today(), -3), frappe.datetime.get_today()]
		},
		{
			"fieldname": "growth_method",
			"label": __("Growth Method"),
			"fieldtype": "Select",
			"options": [
				"", // Blank option to show all
				"Soil-Based",
				"Hydroponic"
			],
			/**
			 * This 'on_change' event is the key. It fires whenever the
			 * 'Growth Method' filter value is changed.
			 */
			"on_change": function() {
				// Get the query report object
				let report = frappe.query_report;

				// Get the current value of the growth_method filter
				let growth_method = report.get_filter_value('growth_method');
				
				// Get the 'crop_cycle' filter object so we can modify it
				let crop_cycle_filter = report.get_filter('crop_cycle');

				if (growth_method) {
					// If a growth method is selected, apply a filter
					crop_cycle_filter.df.get_query = function() {
						return {
							filters: {
								'growth_method': growth_method
							}
						};
					};
				} else {
					// If the growth method is cleared, remove the filter
					crop_cycle_filter.df.get_query = null;
				}

				// Clear any previously selected value in the crop_cycle filter
				// because the list of options has changed.
				report.set_filter_value('crop_cycle', '');
			}
		},
		{
			"fieldname": "crop_cycle",
			"label": __("Specific Crop Cycle"),
			"fieldtype": "Link",
			"options": "Crop Cycle"
		}
	]
};