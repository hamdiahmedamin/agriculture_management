// Create a global namespace for your app to avoid conflicts
frappe.provide('agriculture');
frappe.provide('agriculture.utils');

/**
 * A reusable, global helper function to populate a child table (grid) from a server-side API call.
 * @param {object} frm - The form object.
 * @param {string} api_method - The dotted path to the server-side API method.
 * @param {object} api_args - The arguments to pass to the API method.
 * @param {string} child_table_name - The fieldname of the child table on the form.
 * @param {object} field_map - A map of {source_field_from_api: target_field_in_table}.
 */
agriculture.utils.render_dashboard_grid = function(frm, api_method, api_args, child_table_name, field_map) {
    // Show a message to the user that data is loading
    frappe.show_alert({ message: __('Refreshing...'), indicator: 'blue' });

    if (frm.fields_dict[child_table_name]) {
        // Clear the table of any old data first
        frm.clear_table(child_table_name);

        frappe.call({
            method: api_method,
            args: api_args,
            callback: function (r) {
                if (r.message && Array.isArray(r.message) && r.message.length > 0) {
                    // Loop through the data returned by the API
                    r.message.forEach(data_row => {
                        // Add a new row to the child table
                        let child_row = frm.add_child(child_table_name);
                        // Map the data from the API response to the fields in the new row
                        for (let source_field in field_map) {
                            let target_field = field_map[source_field];
                            child_row[target_field] = data_row[source_field];
                        }
                    });
                }
                // Refresh the grid to display the new rows
                frm.refresh_field(child_table_name);
            }
        });
    }
}