/* eslint-disable */
// Client-side script for Hydroponic Crop Cycle - FINAL VERSION

frappe.ui.form.on('Hydroponic Crop Cycle', {
	refresh: function(frm) {
		frm.remove_custom_button('View Environment History');

		if (!frm.is_new() && frm.doc.pests_incidents && frm.doc.pests_incidents.length > 0) {
			frm.add_custom_button(__('View Environment History'), function() {
				select_incident_for_analysis(frm);
			});
		}
	}
});

function select_incident_for_analysis(frm) {
	const incident_options = frm.doc.pests_incidents.map(incident => {
		return {
			label: `${incident.incident_name} (Reported: ${frappe.datetime.str_to_user(incident.date_reported)})`,
			value: incident.name
		};
	});

	let dialog = new frappe.ui.Dialog({
		title: __('Select Incident to Analyze'),
		fields: [
			{
				label: 'Pest/Disease Incident',
				fieldname: 'selected_incident',
				fieldtype: 'Select',
				options: incident_options,
				reqd: 1
			},
			{
				label: 'Days Before Incident to Analyze',
				fieldname: 'days_prior',
				fieldtype: 'Int',
				default: 5,
				reqd: 1
			}
		],
		primary_action_label: __('Generate Report'),
		primary_action(values) {
			const selected_incident_row = frm.doc.pests_incidents.find(inc => inc.name === values.selected_incident);
			
			if (selected_incident_row) {
				view_environment_history_report(frm, selected_incident_row, values.days_prior);
			}
			dialog.hide();
		}
	});

	dialog.show();
}

function view_environment_history_report(frm, incident, days_prior) {
	if (!frm.doc.linked_locations || frm.doc.linked_locations.length === 0) {
		frappe.msgprint(__("Cannot generate report: No locations are linked to this Crop Cycle."));
		return;
	}

	// --- THE FIX IS HERE ---
	// The field name inside the 'Linked Location' child table is 'location'.
	const location_to_check = frm.doc.linked_locations[0].location; // <-- Changed from 'land_unit' to 'location'
	
	if (!location_to_check) {
		frappe.msgprint(__("Cannot generate report: The 'location' field in the Linked Locations table is empty."));
		return;
	}

	const observation_date = incident.date_reported;
	const start_date = frappe.datetime.add_days(observation_date, -days_prior);

	const filters = {
		location: location_to_check,
		log_timestamp: ["between", [start_date, observation_date]]
	};

	frappe.set_route("Report", "Environment Log", filters);
}