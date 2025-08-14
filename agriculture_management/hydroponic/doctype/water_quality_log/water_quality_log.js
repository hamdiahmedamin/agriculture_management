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
		// Use frm.doc.crop_cycle (or your custom fieldname)
		if (frm.doc.crop_cycle) {
			frappe.call({
				method: 'frappe.client.get',
				args: {
					// --- FIX IS HERE ---
					// Was 'Crop Cycle', now correctly points to your custom DocType.
					doctype: 'Hydroponic Crop Cycle',
					name: frm.doc.crop_cycle,
				},
				callback: function(r) {
					if (r.message && r.message.nutrient_recipe) {
						fetch_recipe_targets(frm, r.message.nutrient_recipe);
					} else {
						clear_target_fields(frm);
					}
				}
			});
		} else {
			clear_target_fields(frm);
		}
	},
	setup: function(frm) {
		// This also uses 'crop_cycle' as the trigger name.
		if (frm.doc.crop_cycle) {
			frm.trigger('crop_cycle');
		}
	}
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