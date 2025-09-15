// Copyright (c) 2025, aminos and contributors
// For license information, please see license.txt

frappe.query_reports["Chart - Water Quality"] = {
	"filters": [
		{
			"fieldname": "hydroponic_system",
			"label": __("Hydroponic System"),
			"fieldtype": "Link",
			"options": "Asset",
			"reqd": 1, // Keeping this not required to allow the dashboard to load

			/**
			 * THIS IS THE NEW, ENHANCED LOGIC.
			 * This function runs every time the user clicks the dropdown.
			 */
			"get_query": function() {
				// This function must return an object with a 'filters' key.
				return {
					"filters": {
						// Filter 1: Only show assets from the correct category.
						"asset_category": "Hydroponic Systems",

						// Filter 2: Only show assets where the status is NOT 'Cancelled'.
						// The ['!=', 'Value'] syntax means "not equal to".
						"status": ["!=", "Cancelled"]
					}
				};
			}
		}
	]
};