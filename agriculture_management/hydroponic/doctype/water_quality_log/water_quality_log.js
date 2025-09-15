/* eslint-disable */
// Client-side script for Water Quality Log DocType
// CORRECTED VERSION for Hydroponic Crop Cycle

frappe.ui.form.on('Water Quality Log', {
	/**
	 * NOTE: The fieldname 'crop_cycle' below must match the "Field Name"
	 * in your Water Quality Log DocType that links to your Hydroponic Crop Cycle.
	 * If you renamed it to 'hydroponic_crop_cycle', change the line below too.
	 */
	crop_cycle: function(frm) {
        // Clear the old target values first
        frm.set_value('target_ph', null);
        frm.set_value('target_ec', null);

        if (frm.doc.crop_cycle) {
            // Call our new whitelisted Python function
            frappe.call({
                method: "agriculture_management.hydroponic.doctype.water_quality_log.water_quality_log.get_targets_from_crop_cycle",
                args: {
                    crop_cycle_name: frm.doc.crop_cycle
                },
                callback: function(r) {
                    if (r && r.message) {
                        // Set the read-only target fields with the data from the server
                        frm.set_value('target_ph', r.message.target_ph);
                        frm.set_value('target_ec', r.message.target_ec);
                    }
                }
            });
        }
    },
	setup: function(frm) {
		// This also uses 'crop_cycle' as the trigger name.
		if (frm.doc.crop_cycle) {
			frm.trigger('crop_cycle');
		}
	},
	refresh: function(frm) {
        // Run our visibility check as soon as the form loads.
        toggle_crop_cycle_visibility(frm);
    },
	hydroponic_system: function(frm) {
        // When the system changes, the old crop cycle is no longer valid.
        frm.set_value('crop_cycle', null);

        // Re-run the visibility check.
        toggle_crop_cycle_visibility(frm);
    },
	onload: function(frm) {
		// Filter the template to only show 'Sanitization' templates
        frm.set_query('hydroponic_system', function() {
            return {
                filters: {
                    'asset_category': 'Hydroponic Systems',
					"status": ["!=", "Cancelled"]
                }
            };
        });
		frm.set_query('crop_cycle', function() {
            return {
                filters: {
                    'hydroponic_system': frm.doc.hydroponic_system
                }
            };
        });
    },
});

function fetch_recipe_targets(frm, recipe_name) {
	frappe.call({
		method: 'frappe.client.get',
		args: {
			doctype: 'Nutrient Recipe',
			name: recipe_name
		},
		callback: function(r) {
			if (r.message) {
				const recipe = r.message;
				const target_ph = recipe.target_ph || '?';
				const target_ec = recipe.target_ec || '?';

				frm.set_value('target_ph', target_ph);
				frm.set_value('target_ec', target_ec);
				
				frm.refresh_field('target_ph');
				frm.refresh_field('target_ec');
			}
		}
	});
}

function clear_target_fields(frm) {
	frm.set_value('target_ph', '');
	frm.set_value('target_ec', '');
	frm.refresh_field('target_ph');
	frm.refresh_field('target_ec');
}

/**
 * HELPER function to control the visibility of the 'crop_cycle' field.
 * @param {object} frm - The current form object.
 */
function toggle_crop_cycle_visibility(frm) {
    // The condition is simple: is the 'hydroponic_system' field filled?
    // The '!!' operator is a clean way to convert a value (even a string) to a true/false boolean.
    let should_show = !!frm.doc.hydroponic_system;

    // Use frm.toggle_display to show or hide the field.
    frm.toggle_display('crop_cycle', should_show);

    // Optional but recommended: also make it mandatory when visible.
    frm.set_df_property('crop_cycle', 'reqd', should_show ? 1 : 0);
}