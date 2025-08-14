frappe.ui.form.on('Harvest Log', {
	 onload: function(frm) {
        // This event runs when the form first loads, including after an amendment.
        if (frm.is_new() && frm.doc.amended_from) {
            // This is an amended document. We must reset its state.
            frm.set_value('status', 'Pending Stock Entry');
            frm.set_value('generated_stock_entry', null);
            
            // Loop through the child table and clear the QI link from each row.
            frm.doc.harvested_items.forEach(item => {
                item.quality_inspection = null;
            });
            frm.refresh_field('harvested_items');

            // --- THIS IS THE DEFINITIVE FIX FOR THE ALERT ---
            // Fetch the Agriculture Settings to display the correct message.
            frappe.db.get_doc("Agriculture Settings").then(settings => {
                let message = __('Document amended. Please review and save.');
                
                // If the setting is checked, provide more specific instructions.
                if (settings.qi_mandatory_for_harvest) {
                    message = __("Document amended. Please SAVE this draft before creating new Quality Inspections for the items below.");
                }

                frappe.show_alert({
                    message: message,
                    indicator: 'orange'
                });
            });
            // --- END OF FIX ---
        }
    },

	refresh: function (frm) {
		// Fetch the global setting first
		frappe.db.get_doc("Agriculture Settings").then(settings => {
			frm.clear_custom_buttons(); // Clear old buttons before adding new ones

			// --- Logic for Draft Documents (docstatus 0) ---
			if (frm.doc.docstatus === 0) {
				// Button to create Quality Inspections (always available in draft)
                if (!frm.is_new() && frm.doc.harvested_items && frm.doc.harvested_items.length > 0) {
                    frm.add_custom_button(__('Create Quality Inspection'), function() {
                        create_quality_inspections_dialog(frm);
                    });
                }
			}

			// --- Logic for Submitted Documents (docstatus 1) ---
			if (frm.doc.docstatus === 1) {
				// If QI is NOT mandatory AND no stock entry exists, show the "Create Stock Entry" button
				if (!settings.qi_mandatory_for_harvest && !frm.doc.generated_stock_entry) {
					frm.add_custom_button(__('Create Stock Entry'), function () {
						// This button is now a direct action, no confirmation needed if QI is optional
						frm.call('create_stock_entry_from_harvest').then(r => {
							if (r.message) frm.reload_doc();
						});
					}).addClass('btn-primary');
				}

				// Add a link to the generated Stock Entry if it exists
				if (frm.doc.generated_stock_entry) {
					frm.add_custom_button(__('View Stock Entry'), function () {
						frappe.set_route('Form', 'Stock Entry', frm.doc.generated_stock_entry);
					}).addClass('btn-secondary');
				}
			}
		});
	}
});

function create_quality_inspections_dialog(frm) {
	// 1. Find which items in the table ALREADY have a QI for this Harvest Log
	frappe.db.get_list("Quality Inspection", {
		filters: { reference_type: "Harvest Log", reference_name: frm.doc.name },
		fields: ["item_code"]
	}).then(existing_qis => {
		const inspected_items = existing_qis.map(qi => qi.item_code);

		// 2. Build a list of items that are NOT yet inspected
		const items_to_inspect_options = frm.doc.harvested_items
			.filter(item => !inspected_items.includes(item.item_code))
			.map(item => ({
				label: `${item.item_name || item.item_code} (Qty: ${item.quantity})`,
				value: item.item_code,
				checked: 1 // Default to checked
			}));

		if (items_to_inspect_options.length === 0) {
			frappe.msgprint(__("All items in this harvest already have a Quality Inspection created."));
			return;
		}

		// 3. Create and show the dialog
		const dialog = new frappe.ui.Dialog({
			title: __("Select Items for Quality Inspection"),
			fields: [
				{
					fieldname: 'items_to_inspect',
					fieldtype: 'MultiCheck',
					label: __('Harvest Items to Inspect'),
					options: items_to_inspect_options,
					columns: 2
				}
			],
			primary_action_label: __("Create Selected QIs"),
			primary_action(values) {
				if (!values.items_to_inspect || values.items_to_inspect.length === 0) {
					frappe.msgprint(__("Please select at least one item."));
					return;
				}

				const selected_items_data = values.items_to_inspect.map(item_code => {
					return frm.doc.harvested_items.find(item => item.item_code === item_code);
				});

				// Call the instance method on the Harvest Log document
				frappe.call({
					method: "agriculture_management.agriculture.api.create_qis_for_harvest_items",
					args: {
						harvest_log_name: frm.doc.name, // Manually pass the document name
						items_to_inspect: selected_items_data
					},
					callback: function (r) {
						if (r.message && r.message.length > 0) {
							frappe.msgprint({
								title: __('Success'),
								message: __("{0} Quality Inspection(s) created.", [r.message.length]),
								indicator: 'green'
							});
							frm.reload_doc(); // Reload to see the linked QIs in the child table
						}
					}
				});

				dialog.hide();
			}
		});

		dialog.show();
	});
}