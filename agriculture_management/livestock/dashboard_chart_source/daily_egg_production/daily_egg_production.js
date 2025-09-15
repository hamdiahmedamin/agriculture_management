// Copyright (c) 2025, aminos and contributors
// For license information, please see license.txt
/* eslint-disable */

frappe.provide('frappe.dashboards.chart_sources');

frappe.dashboards.chart_sources["Daily Egg Production"] = {
	method: "agriculture_management.livestock.api.get_total_daily_egg_production",
	filters: [

	]
};
