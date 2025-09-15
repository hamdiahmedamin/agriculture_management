/*
* pest_and_disease_log.js
* Adds intelligent features to the Pest and Disease Log form.
*/
frappe.ui.form.on('Pest and Disease Log', {
    /**
     * ONLOAD: Set up filters that depend on other fields on this form.
     */
    onload: function(frm) {
        // Filter for pest/disease name based on the observation type
        frm.set_query('pest_or_disease', function() {
            if (!frm.doc.observation_type) {
                frappe.throw(__("Please select an Observation Type first."));
            }
            return {
                filters: {
                    'type': frm.doc.observation_type
                }
            };
        });
    },

    /**
     * CROP CYCLE (on change): This is the main trigger for fetching context.
     */
    crop_cycle: function(frm) {
        // Clear all dependent fields first
        frm.set_value('growth_method', null);
        frm.set_value('company', null);
        frm.set_value('location', null);
        frm.set_value('growing_zone', null);

        if (frm.doc.crop_cycle) {
            // Call our new whitelisted Python function
            frappe.call({
                method: "agriculture_management.agriculture.api.get_log_context",
                args: {
                    crop_cycle_name: frm.doc.crop_cycle
                },
                callback: function(r) {
                    if (r.message) {
                        let data = r.message;
                        
                        // Set the read-only and context fields
                        frm.set_value('growth_method', data.growth_method);
                        frm.set_value('company', data.company);

                        // --- Intelligent Location/Zone Filtering ---
                        if (data.growth_method === 'Soil-Based') {
                            // Pre-fill the soil-based location field
                            frm.set_value('location', data.land_unit); // Using correct fieldname 'land_unit'
                        } 
                        else if (data.growth_method === 'Hydroponic') {
                            // For hydroponics, filter the 'growing_zone' dropdown to only show
                            // zones that are actually part of the selected Crop Cycle.
                            frm.set_query('growing_zone', function() {
                                return {
                                    filters: {
                                        // The 'name' of the Growing Zone must be in the list
                                        // we fetched from the Crop Cycle's child table.
                                        'name': ['in', data.growing_zones]
                                    }
                                };
                            });
                        }
                    }
                }
            });
        }
    },

    /**
     * OBSERVATION TYPE (on change): Clear the dependent field.
     */
    observation_type: function(frm) {
        frm.set_value('pest_or_disease', null);
    }
});