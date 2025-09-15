/*
* daily_hydroponic_log.js
* Adds automation to the Daily Hydroponic Log.
*/
frappe.ui.form.on('Daily Hydroponic Log', {
    onload: function(frm) {
		// Filter the template to only show 'Sanitization' templates

		frm.set_query('crop_cycle', function() {
            return {
                filters: {
                    'company': frm.doc.company
                }
            };
        });
    },
    /**
     * CROP CYCLE (on change): Fetches context data from the selected Crop Cycle.
     */
    crop_cycle: function(frm) {
        frm.set_value('company', null);
        frm.set_value('hydroponic_system', null);

        if (frm.doc.crop_cycle) {
            // We can re-use the same powerful whitelisted function
            frappe.call({
                method: "agriculture_management.agriculture.api.get_log_context",
                args: {
                    crop_cycle_name: frm.doc.crop_cycle
                },
                callback: function(r) {
                    if (r && r.message) {
                        let data = r.message;
                        frm.set_value('company', data.company);
                        frm.set_value('hydroponic_system', data.hydroponic_system);
                    }
                }
            });
        }
    },

    /**
     * REFRESH: Adds a custom button to create a more detailed log if needed.
     */
    refresh: function(frm) {
        // Add a button to quickly create a detailed Water Quality Log from this daily log
        if (!frm.is_new() && frm.doc.docstatus === 0) {
            frm.add_custom_button(__('Create Detailed Water Quality Log'), function() {
                frappe.new_doc('Water Quality Log', {
                    crop_cycle: frm.doc.crop_cycle,
                    hydroponic_system: frm.doc.hydroponic_system,
                    company: frm.doc.company,
                    measured_ph: frm.doc.measured_ph,
                    measured_ec_mscm: frm.doc.measured_ec_mscm,
                    water_temperature_c: frm.doc.water_temperature_c
                });
            });
        }
    },

    /**
     * DOSING PERFORMED (on change): If the user checks this box,
     * prompt them to create a full Dosing Log.
     */
    dosing_performed: function(frm) {
        if (frm.doc.dosing_performed) {
            frappe.confirm(
                'Do you want to create a detailed Dosing Log for this event?',
                () => {
                    // If 'Yes'
                    frappe.new_doc('Dosing Log', {
                        crop_cycle: frm.doc.crop_cycle,
                        hydroponic_system: frm.doc.hydroponic_system,
                        company: frm.doc.company,
                        dosing_date: frm.doc.log_date
                    });
                },
                () => {
                    // If 'No', do nothing. User can link it manually.
                }
            );
        }
    }
});