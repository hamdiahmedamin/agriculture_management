// Copyright (c) 2017, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt
/*
* plant_analysis.js
* Adds automation and dynamic filters to the Plant Analysis form.
*/
frappe.ui.form.on('Plant Analysis', {
    /**
     * ONLOAD: Auto-load the criteria table if it's a new document.
     */
    onload: function(frm) {
        if (frm.is_new() && !frm.doc.plant_analysis_criteria.length) {
            frm.call('load_contents');
        }
    },

    /**
     * CROP CYCLE (on change): Fetches context data and sets up filters.
     */
    crop_cycle: function(frm) {
        // Clear all dependent fields first
        frm.set_value('company', null);
        frm.set_value('growth_method', null);
        frm.set_value('land_unit', null);
        frm.set_value('growing_zone', null);

        if (frm.doc.crop_cycle) {
            // Re-use our secure, whitelisted API function
            frappe.call({
                method: "agriculture_management.agriculture.api.get_log_context",
                args: {
                    crop_cycle_name: frm.doc.crop_cycle
                },
                callback: function(r) {
                    if (r && r.message) {
                        let data = r.message;
                        
                        // Set the Company and the hidden growth_method field
                        frm.set_value('company', data.company);
                        frm.set_value('growth_method', data.growth_method);

                        // Set up cascading filters for the location/zone fields
                        if (data.growth_method === 'Soil-Based') {
                            frm.set_value('land_unit', data.land_unit);
                        } 
                        else if (data.growth_method === 'Hydroponic') {
                            frm.set_query('growing_zone', function() {
                                return {
                                    filters: {
                                        'name': ['in', data.growing_zones]
                                    }
                                };
                            });
                        }
                    }
                }
            });
        }
    }
});