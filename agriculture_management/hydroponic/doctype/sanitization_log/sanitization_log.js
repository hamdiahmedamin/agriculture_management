/* eslint-disable */
// FINAL SCRIPT - Calling a dedicated server function for the lookup.

frappe.ui.form.on('Sanitization Chemical', {
	/**
	 * This trigger fires when the 'sanitizing_agent' (the Item link) is changed.
	 */
	sanitizing_agent: function(frm, cdt, cdn) {
		let row = locals[cdt][cdn];

		if (row.sanitizing_agent) {
			
			let company = frm.doc.company || frappe.defaults.get_user_default("company");

			if (!company) {
				frappe.msgprint(__("Please set a Company on the form to fetch the default warehouse."));
				return;
			}
			
			// This is the new, robust method. We call our custom Python API function.
			frappe.call({
				method: 'agriculture_management.hydroponic.api.get_item_default_warehouse', // <-- IMPORTANT: Change 'your_custom_app'
				args: {
					item_code: row.sanitizing_agent,
					company: company
				},
				callback: function(r) {
					// The response 'r.message' will contain the warehouse name directly, or be empty.
					if (r.message) {
						// Set the value in our grid row.
						frappe.model.set_value(cdt, cdn, 'source_warehouse', r.message);
					}
				}
			});
		}
	}
});