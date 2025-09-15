/* eslint-disable */
// Client Script for Planting Schedule (Frappe v15)

frappe.ui.form.on('Planting Schedule', {
	/**
	 * REFRESH: Runs on form load.
	 */
	refresh: function(frm) {
		setup_create_crop_cycle_button(frm);
	},

	/**
	 * When the parent 'hydroponic_system' field changes,
	 * clear the child table to force re-selection of zones.
	 */
	hydroponic_system: function(frm) {
		if (frm.doc.growing_zones && frm.doc.growing_zones.length > 0) {
			frm.clear_table('growing_zones');
			frm.refresh_field('growing_zones');
			frappe.msgprint(__('Growing zones cleared. Please re-select zones for the new system.'));
		}
	},

	/**
	 * DATE CALCULATION: When the user enters a start date or duration,
	 * automatically calculate the estimated harvest date.
	 */
	target_planting_date: function(frm) {
		calculate_harvest_date(frm);
	},
	estimated_days_to_harvest: function(frm) {
		calculate_harvest_date(frm);
	}
});

/**
 * CHILD TABLE EVENTS: This targets the 'growing_zones' child table
 * to set up the cascading filter.
 */
frappe.ui.form.on('Planting Schedule Zone', {
	/**
	 * Before the form for a new row is rendered, set the filter.
	 */
	growing_zones_add: function(frm) {
		set_growing_zone_filter(frm);
	},
	/**
	 * When an existing row is loaded, also set the filter.
	 */
	form_render: function(frm, cdt, cdn) {
		set_growing_zone_filter(frm);
	}
});

/**
 * HELPER: Sets the dynamic query on the 'growing_zone' field in the child table.
 */
function set_growing_zone_filter(frm) {
	let grid = frm.get_field('growing_zones').grid;
	grid.get_field('growing_zone').get_query = function(doc, cdt, cdn) {
		let parent_system = frm.doc.hydroponic_system;
		if (!parent_system) {
			frappe.throw(__('Please select a <b>Hydroponic System</b> first to choose a growing zone.'));
		}
		return {
			filters: {
				'hydroponic_system': parent_system
			}
		};
	};
}

/**
 * HELPER: Calculates the estimated harvest date.
 */
function calculate_harvest_date(frm) {
	if (frm.doc.target_planting_date && frm.doc.estimated_days_to_harvest > 0) {
		let harvest_date = frappe.datetime.add_days(frm.doc.target_planting_date, frm.doc.estimated_days_to_harvest);
		frm.set_value('estimated_harvest_date', harvest_date);
	}
}

/**
 * HELPER: Shows or hides the "Create Crop Cycle" button.
 */
function setup_create_crop_cycle_button(frm) {
	frm.remove_custom_button('Create Crop Cycle');
	if (!frm.is_new() && frm.doc.status === 'Planned' && !frm.doc.linked_crop_cycle) {
		frm.add_custom_button(__('Create Crop Cycle'), function() {
			create_crop_cycle_from_plan(frm);
		});
	}
}

/**
 * HELPER: Creates a new Crop Cycle document from the plan.
 * This is the modern, correct version for Frappe v15.
 * @param {object} frm - The current form object.
 */
function create_crop_cycle_from_plan(frm) {
    console.log("Starting create_crop_cycle_from_plan...");

    // 1. Prepare all data to be passed in a single object
    var data_to_pass = {
        // Parent fields
        crop: frm.doc.crop,
        start_date: frm.doc.target_planting_date,
        end_date: frm.doc.estimated_harvest_date, // <-- ADDED THIS LINE
        status: 'Planned', // <-- ADDED THIS LINE
        company: frm.doc.company,
        linked_planting_schedule: frm.doc.name,
        growth_method: frm.doc.is_hydroponic_schedule ? 'Hydroponic' : 'Soil-Based',
        hydroponic_system: frm.doc.is_hydroponic_schedule ? frm.doc.hydroponic_system : null,
        location: !frm.doc.is_hydroponic_schedule ? frm.doc.location : null,
        // Child table data
        growing_zones: []
    };

    if (frm.doc.is_hydroponic_schedule && frm.doc.growing_zones) {
        data_to_pass.growing_zones = frm.doc.growing_zones.map(function(source_row) {
            return { 'growing_zone': source_row.growing_zone };
        });
    }

    // 2. Save the entire object to local storage
    localStorage.setItem('new_crop_cycle_data', JSON.stringify(data_to_pass));
    
    console.log("Data saved to local storage:", data_to_pass);

    // 3. Open the new document form
    frappe.new_doc('Crop Cycle');
}