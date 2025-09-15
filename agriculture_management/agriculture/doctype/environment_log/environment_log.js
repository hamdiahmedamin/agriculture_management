// Copyright (c) 2025, aminos and contributors
// For license information, please see license.txt

/*
* environment_log.js
* Adds automation and dynamic fields to the Environment Log form.
*/
frappe.ui.form.on('Environment Log', {
    /**
     * CROP CYCLE (on change): This is the main trigger.
     */
    crop_cycle: function(frm) {
        // Clear all dependent fields first
        frm.set_value('company', null);
        frm.set_value('growth_method', null);
        frm.set_value('land_unit', null);
        frm.set_value('growing_zone', null);

        if (frm.doc.crop_cycle) {
            // We can re-use the same powerful whitelisted API function from our api.py file
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
                            // For soil, pre-fill the location and make it read-only
                            frm.set_value('land_unit', data.land_unit);
                        } 
                        else if (data.growth_method === 'Hydroponic') {
                            // For hydroponics, filter the 'growing_zone' dropdown to show
                            // only zones that are actually part of the selected Crop Cycle.
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