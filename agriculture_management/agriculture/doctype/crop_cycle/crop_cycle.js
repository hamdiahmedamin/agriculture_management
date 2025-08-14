frappe.ui.form.on('Crop Cycle', {
    setup: function(frm) {
        // This filter is correct. It filters the 'hydroponic_system' link field
        // to only show Assets from the 'Hydroponic Systems' category.
        frm.set_query('hydroponic_system', function() {
            return { filters: { 'asset_category': 'Hydroponic Systems' } };
        });
    },

    onload: function(frm) {
        // This is correct. It sets the default Naming Series when creating a new document.
        if (frm.is_new() && !frm.doc.naming_series) {
            frm.trigger("growth_method");
        }
    },

    growth_method: function(frm) {
        // This is correct. It updates the Naming Series if the method is changed.
        if (frm.is_new()) {
            frm.set_value('naming_series', frm.doc.growth_method === 'Hydroponic' ? 'HCC-.YYYY.-' : 'CC-.YYYY.-');
        }
    },

    refresh: function(frm) {
        // Only show buttons for saved documents
        if (frm.is_new()) {
            return;
        }

        // --- Cleaned Up and Corrected Buttons ---

        // 1. Update Dashboard Button (Universal)
        frm.add_custom_button(__('Update Dashboard'), () => {
            frm.call('update_dashboard_totals').then(() => {
                frm.refresh_fields(); // Use refresh_fields() for a lighter reload
                frappe.show_alert({message: __('Dashboard totals have been updated.'), indicator: 'green'});
            });
        });

        // 2. Record New Harvest Button (Universal)
        // This is the NEW primary action for harvesting.
        frm.add_custom_button(__('Record New Harvest'), () => {
            frappe.new_doc("Harvest Log", {
                crop_cycle: frm.doc.name,
                company: frm.doc.company
                // You can pre-fill other fields here if needed
            });
        }).addClass('btn-primary'); // Make it the primary button

        // 3. Conditional Button: View Environment History (for Hydroponics)
        if (frm.doc.growth_method === 'Hydroponic' && frm.doc.agronomic_incidents && frm.doc.agronomic_incidents.length > 0) {
            frm.add_custom_button(__('View Environment History'), function() {
                select_incident_for_analysis(frm);
            });
        }
    }
});

// --- Helper Functions (These remain useful) ---
function select_incident_for_analysis(frm) {
    // This function for the incident analysis dialog is correct.
    // Ensure the child table fieldname is 'agronomic_incidents'.
    if (!frm.doc.agronomic_incidents || frm.doc.agronomic_incidents.length === 0) {
        frappe.msgprint(__("No incidents to analyze."));
        return;
    }
    
	const incident_options = frm.doc.agronomic_incidents.map(incident => {
		return {
			label: `${incident.incident_name} (Reported: ${frappe.datetime.str_to_user(incident.date_reported)})`,
			value: incident.name
		};
	});

	let dialog = new frappe.ui.Dialog({
		title: __('Select Incident to Analyze'),
		fields: [ /* ... your dialog fields are correct ... */ ],
		primary_action_label: __('Generate Report'),
		primary_action(values) {
			const selected_incident_row = frm.doc.agronomic_incidents.find(inc => inc.name === values.selected_incident);
			if (selected_incident_row) {
				view_environment_history_report(frm, selected_incident_row, values.days_prior);
			}
			dialog.hide();
		}
	});
	dialog.show();
}

function view_environment_history_report(frm, incident, days_prior) {
    // This function is also correct.
    if (!frm.doc.hydroponic_system) {
		frappe.msgprint(__("Cannot generate report: No Hydroponic System is linked to this Crop Cycle."));
		return;
	}
	const observation_date = incident.date_reported;
	const start_date = frappe.datetime.add_days(observation_date, -days_prior);
	const filters = {
		hydroponic_system: frm.doc.hydroponic_system,
		log_timestamp: ["between", [start_date, observation_date]]
	};
	frappe.set_route("Report", "Environment Log", filters);
}