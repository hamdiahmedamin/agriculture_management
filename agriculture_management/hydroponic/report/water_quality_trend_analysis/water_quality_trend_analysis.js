// Copyright (c) 2025, aminos and contributors
// For license information, please see license.txt
/* eslint-disable */

frappe.query_reports["Water Quality Trend Analysis"] = {
	"filters": [
		{
			"fieldname": "hydroponic_system",
			"label": __("Hydroponic System"),
			"fieldtype": "Link",
			"options": "Asset",
			// Add a filter to only show assets from the "Hydroponic Systems" category
			"get_query": function() {
				return {
					filters: {
						"asset_category": "Hydroponic Systems"
					}
				};
			},
			"reqd": 1
		},
		{
			"fieldname": "date_range",
			"label": __("Date Range"),
			"fieldtype": "DateRange",
			"reqd": 1
		}
	],

	"get_chart_data": function(columns, result) {
		// Prepare the labels for the X-axis (the timestamps)
		const labels = result.map(d => frappe.datetime.format_date(d.log_timestamp));

		// Prepare the datasets for the Y-axis using your exact fieldnames
		const datasets = [
			{
				"name": "Measured pH",
				"type": "line",
				"values": result.map(d => d.measured_ph)
			},
			{
				"name": "Measured EC",
				"type": "line",
				"values": result.map(d => d.measured_ec_mscm)
			},
			{
				"name": "Water Temp (°C)",
				"type": "line",
				"values": result.map(d => d.water_temperature_c)
			}
		];
		
		return {
			"data": {
				"labels": labels,
				"datasets": datasets,
			},
			"type": "line",
			"height": 280,
			"colors": ['#00A8F0', '#FFA00A', '#DD4B39'] // Blue, Orange, Red
		};
	}
};