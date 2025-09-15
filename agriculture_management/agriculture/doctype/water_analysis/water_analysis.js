// Copyright (c) 2017, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on('Water Analysis', {
	onload: (frm) => {
		if (frm.doc.water_analysis_criteria.length ==0) frm.call('load_contents');
	},
	refresh: (frm) => {
		let map_tools = ["a.leaflet-draw-draw-polyline",
			"a.leaflet-draw-draw-polygon",
			"a.leaflet-draw-draw-rectangle",
			"a.leaflet-draw-draw-circle",
			"a.leaflet-draw-draw-circlemarker"];

		map_tools.forEach((element) => $(element).hide());
	},
	laboratory_testing_datetime: (frm) => frm.call("update_lab_result_date"),
	  /**
     * CROP CYCLE (on change): Fetches context data from the selected Crop Cycle.
     */
    crop_cycle: function(frm) {
        // Clear dependent fields
        frm.set_value('company', null);
        frm.set_value('water_source', null);

        if (frm.doc.crop_cycle) {
            // Call our enhanced whitelisted Python function
            frappe.call({
                method: "agriculture_management.agriculture.api.get_log_context",
                args: {
                    crop_cycle_name: frm.doc.crop_cycle
                },
                callback: function(r) {
                    if (r && r.message) {
                        let data = r.message;
                        
                        // Set the values for Company and the Water Source that was found
                        // through the multi-level lookup on the server.
                        frm.set_value('company', data.company);
                        frm.set_value('water_source', data.water_source);
                    }
                }
            });
        }
    }
});