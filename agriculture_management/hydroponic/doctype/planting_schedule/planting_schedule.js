/* eslint-disable */
// Client-side script for Planting Schedule

frappe.ui.form.on('Planting Schedule', {
	/**
	 * When the user enters the target planting date or the estimated days to harvest,
	 * automatically calculate the estimated harvest date.
	 */
	target_planting_date: function(frm) {
		calculate_harvest_date(frm);
	},
	estimated_days_to_harvest: function(frm) {
		calculate_harvest_date(frm);
	},

	/**
	 * The refresh event runs every time the form is loaded.
	 * It controls when the "Create Crop Cycle" button should be visible.
	 */
	refresh: function(frm) {
		// Clear button first to prevent duplicates
		frm.remove_custom_button('Create Hydroponic Crop Cycle');

		// Show the button only if the document is saved, in 'Planned' status,
		// and has NOT been linked to a crop cycle yet.
		if (!frm.is_new() && frm.doc.status === 'Planned' && !frm.doc.linked_hydroponic_crop_cycle) {
			frm.add_custom_button(__('Create Hydroponic Crop Cycle'), function() {
				create_crop_cycle_from_plan(frm);
			});
		}
	}
});

/**
 * Helper function to calculate the estimated harvest date.
 * @param {object} frm - The current form object.
 */
function calculate_harvest_date(frm) {
	if (frm.doc.target_planting_date && frm.doc.estimated_days_to_harvest > 0) {
		let harvest_date = frappe.datetime.add_days(frm.doc.target_planting_date, frm.doc.estimated_days_to_harvest);
		// Use frm.set_value to ensure dependencies and triggers are fired correctly.
		frm.set_value('estimated_harvest_date', harvest_date);
	}
}

/**
 * Helper function to create a new Hydroponic Crop Cycle document,
 * pre-filling it with data from this Planting Schedule.
 * @param {object} frm - The current form object.
 */
function create_crop_cycle_from_plan(frm) {
	frappe.route_options = {
		// Pre-fill fields in the new Hydroponic Crop Cycle form
		crop_name: frm.doc.crop,
		hydroponic_system: frm.doc.hydroponic_system,
		start_date: frm.doc.target_planting_date,
		// This is a custom field you should add to your Hydroponic Crop Cycle DocType
		// to link it back to the plan.
		custom_linked_planting_schedule: frm.doc.name
	};

	// Open the form for a new Hydroponic Crop Cycle
	frappe.new_doc('Hydroponic Crop Cycle');
}