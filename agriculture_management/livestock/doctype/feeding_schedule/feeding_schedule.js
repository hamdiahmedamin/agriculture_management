// Copyright (c) 2025, aminos and contributors
// For license information, please see license.txt

frappe.ui.form.on("Feeding Schedule", {
    refresh: function(frm) {
        frm.clear_custom_buttons();

        let is_expired = false;
        if (frm.doc.to_date) {
            const to_date_obj = new Date(frm.doc.to_date);
            const today = new Date(frappe.datetime.now_date());

            if (to_date_obj < today) {
                is_expired = true;
            }
        }

        if (!frm.is_new() && is_expired) {
            frm.dashboard.set_headline(__("This schedule's end date has passed. Fields are locked."));

            // Lock fields every time the form refreshes
            ["from_date", "to_date", "livestock_group", "feed_formulation", "status", "feeding_schedule_log"].forEach(f => {
                frm.set_df_property(f, "read_only", 1);
            });

            return;
        }

        // Normal logic if not expired
        if (frm.doc.status !== 'Draft') {
            ["from_date", "to_date", "livestock_group", "feed_formulation", "feeding_schedule_log"].forEach(f => {
                frm.set_df_property(f, "read_only", 1);
            });
        } else {
            ["from_date", "to_date", "livestock_group", "feed_formulation", "feeding_schedule_log"].forEach(f => {
                frm.set_df_property(f, "read_only", 0);
            });
        }

        if (frm.doc.status === 'Draft') {
            frm.add_custom_button(__('Generate Schedule'), function() {
                frm.call('generate_feeding_log').then(() => {
                    frm.reload_doc();
                });
            }).addClass('btn-primary');
        }
    }
});

frappe.ui.form.on("Feeding Schedule Log", {
    // Revert to Draft if the log is cleared
    feeding_schedule_log_remove: function(frm) {
        // This event fires after a row is removed.
        if (!frm.doc.feeding_schedule_log || frm.doc.feeding_schedule_log.length === 0) {
            frappe.confirm(
                __('The schedule log is now empty. Do you want to revert this schedule to Draft status? This will allow you to change the date range and re-generate the log.'),
                () => {
                    // If confirmed, set status to 'Draft' and save.
                    frm.set_value('status', 'Draft');
                    frm.save();
                }
            );
        } else {
            // If rows still exist, we should still recalculate the overall status.
            frm.call('update_overall_status').then(() => {
                frm.refresh_field('status');
            });
        }
    },

    // Action for the button in each row
    complete_button: function(frm, cdt, cdn) {
        let row = locals[cdt][cdn];
        if (row.status !== 'Planned') {
            frappe.msgprint(__("This feeding has already been processed."));
            return;
        }
        // 1. First, fetch the default warehouse from Livestock Settings.
        frappe.db.get_single_value("Livestock Settings", "default_feed_warehouse")
            .then(default_warehouse => {
                
                // 2. Create the dialog with the Source Warehouse field, pre-filled.
                let dialog = new frappe.ui.Dialog({
                    title: __("Confirm Feed Consumption"),
                    fields: [
                        {
                            fieldtype: 'HTML',
                            options: `
                                <p>You are about to consume ingredients for the feeding planned on <strong>${row.date}</strong>.</p>
                                <p>Total Recommended Quantity: <strong>${row.recommended_quantity.toFixed(2)} Kg</strong></p>
                                <hr>
                            `
                        },
                        {
                            label: 'Consume Ingredients From Warehouse',
                            fieldname: 'source_warehouse',
                            fieldtype: 'Link',
                            options: 'Warehouse',
                            default: default_warehouse, // Pre-fill with the default
                            reqd: 1
                        }
                    ],
                    primary_action_label: __('Confirm and Create Stock Entry'),
                    primary_action: (values) => {
                        // 3. Call the server, passing the selected warehouse.
                        frappe.call({
                            doc: frm.doc,
                            method: 'complete_feeding_for_row',
                            args: {
                                row_name: row.name,
                                source_warehouse: values.source_warehouse // Pass the value from the dialog
                            },
                            callback: function(r) {
                                if (r.message) {
                                    dialog.hide();
                                    frappe.show_alert({ message: __("Feeding completed successfully."), indicator: 'green' });
                                    frm.reload_doc();
                                }
                            }
                        });
                    }
                });
                dialog.show();
            });
    }
});

// Helper function for stock availability check
function run_stock_check(frm) {
    // This is a placeholder for your stock check logic.
    // You would typically add a button to trigger this.
    // For example:
    // frm.add_custom_button(__('Check Ingredient Availability'), () => { ... });
}