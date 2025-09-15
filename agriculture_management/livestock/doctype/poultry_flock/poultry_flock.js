// Copyright (c) 2025, aminos and contributors
// For license information, please see license.txt

frappe.ui.form.on('Poultry Flock', {
    setup: function(frm) {
        frm.set_query('strain', function(doc) {
            if (!doc.specie) { frappe.throw(__("Please select a Species first.")); }
            return { filters: { 'species': doc.specie } };
        });
    },

    onload: function(frm) {
        calculate_and_display_age(frm);
    },

    refresh: function(frm) {
    // =================================================================
    // THIS IS THE SINGLE, DEFINITIVE UI CONTROL LOGIC
    // =================================================================

    // --- 1. SETUP: Define UI elements and get the current state ---
    const operational_tabs = [
        'sales_history_tab', 'mortality_history_tab', 'weight_tracking_tab',
        'health_tab', 'financials_tab', 'feeding_history_tab', 'connections_tab'
    ];
    const fields_to_lock = [
        "item", "flock_type", "specie", "strain", "coop", "hatch_date",
        "acquisition_date", "initial_head_count", "cost_center"
    ];
    const weight_grid = frm.fields_dict.weight_tracking_history ? frm.fields_dict.weight_tracking_history.grid : null;

    // --- THIS IS THE DEFINITIVE DATE CHECK FIX ---
    // Use reliable JavaScript Date objects for comparison.
    let is_in_withdrawal = false;
    if (frm.doc.in_withdrawal_until) {
        const withdrawal_end_date = new Date(frm.doc.in_withdrawal_until);
        const today = new Date(frappe.datetime.now_date());
        if (withdrawal_end_date >= today) {
            is_in_withdrawal = true;
        }
    }
    // --- END OF FIX ---

    // --- 2. CLEAR THE FORM TO START FRESH ---
    frm.clear_custom_buttons();
    frm.dashboard.clear_headline();

    // --- 3. APPLY LOGIC BASED ON STATUS ---
    if (frm.is_new() || frm.doc.status === 'Planning') {
        // SCENARIO 1: New or Planning. Hide all operational tabs.
        frm.toggle_display(operational_tabs, false);
        if (!frm.is_new()) {
            frm.add_custom_button(__('Receive Flock into Stock'), () => {
                frappe.call({ doc: frm.doc, method: 'receive_flock_into_stock', callback: (r) => { if (r.message) { frm.reload_doc(); } } });
            }).addClass('btn-primary');
        }
    } else if (frm.doc.status === 'Active' || frm.doc.status === 'In Withdrawal') {
        // SCENARIO 2: Active or In Withdrawal. Show tabs, render buttons based on withdrawal state.
        frm.toggle_display(operational_tabs, true);
        
        fields_to_lock.forEach(field => frm.set_df_property(field, 'read_only', 0));
        frm.toggle_display("record_weight_button", true);
        
        if (weight_grid) {
            weight_grid.meta.fields.forEach(df => { df.read_only = 0; });
            weight_grid.refresh();
        }
        
        // Pass the withdrawal state to the button renderer. It will hide the sell buttons if true.
        render_action_buttons(frm, is_in_withdrawal);

    } else { // Closed states: Sold, Culled, Deceased
        // SCENARIO 3: Closed. Show all history tabs but lock everything down.
        frm.toggle_display(operational_tabs, true);
        frm.toggle_display("record_weight_button", false);

        fields_to_lock.forEach(field => frm.set_df_property(field, 'read_only', 1));

        if (weight_grid) {
            weight_grid.meta.fields.forEach(df => { df.read_only = 1; });
            weight_grid.refresh();
        }
        
        frm.dashboard.set_headline(`This flock is ${frm.doc.status}. All fields are read-only.`, 'grey');
    }

    // --- 4. DISPLAY WITHDRAWAL BANNER (if applicable) ---
    // This is now redundant if the status is "In Withdrawal", but serves as a good visual reminder.
    if (is_in_withdrawal) {
        frm.dashboard.set_headline_alert(
            `<strong>Warning: In Withdrawal Period until ${frappe.datetime.str_to_user(frm.doc.in_withdrawal_until)}</strong>. Products cannot be sold.`, 'red'
        );
    }
},
    

    hatch_date: function(frm) {
        calculate_and_display_age(frm);
    },

    flock_type: function(frm) {
        frm.refresh();
    },

    specie: function(frm) {
        if (frm.doc.specie) {
            frm.toggle_display('strain', true);
            frm.set_value('strain', '');
        } else {
            frm.toggle_display('strain', false);
            frm.set_value('strain', '');
        }
    },

    // --- BUTTON EVENTS ---

    refresh_mortality_history: function(frm) {
        agriculture.utils.render_dashboard_grid(frm,
            'agriculture_management.livestock.api.get_flock_mortality_history',
            { poultry_flock_id: frm.doc.name },
            'mortality_history_log',
            { date: 'date', quantity: 'quantity', cause: 'cause', record_type: 'record_type', record: 'record' }
        );
    },

    refresh_sales_history: function(frm) {
        agriculture.utils.render_dashboard_grid(frm,
            'agriculture_management.livestock.api.get_flock_sales_history',
            { poultry_flock_id: frm.doc.name },
            'sales_history_log',
            { date: 'date', customer: 'customer', quantity: 'quantity', rate: 'rate', total_amount: 'total_amount', record_type: 'record_type', record: 'record' }
        );
    },

    record_weight_button: function(frm) {
        frappe.prompt([
            { label: 'Date', fieldname: 'date', fieldtype: 'Date', default: frappe.datetime.now_date(), reqd: 1 },
            { label: 'Average Weight', fieldname: 'average_weight', fieldtype: 'Float', reqd: 1 },
            { label: 'UoM', fieldname: 'uom', fieldtype: 'Link', options: 'UOM', default: 'Kg', reqd: 1 },
            { label: 'Sample Size', fieldname: 'sample_size', fieldtype: 'Int' }
        ], (values) => {
            frm.add_child('weight_tracking_history', values);
            frm.refresh_field('weight_tracking_history');
            frm.save().then(() => frappe.show_alert({ message: __('Weight log saved.'), indicator: 'green' }));
        }, __('Record Average Weight'));
    },

    refresh_health_history: function(frm) {
        agriculture.utils.render_dashboard_grid(frm,
            'agriculture_management.livestock.api.get_flock_health_history',
            { poultry_flock_id: frm.doc.name },
            'health_history_log',
            { date: 'date', event_type: 'event_type', details: 'details', status: 'status', record_type: 'record_type', record: 'record' }
        );
    },

    refresh_financials: function(frm) {
        frappe.show_alert({ message: __('Refreshing...'), indicator: 'blue' });
        frappe.call({
            method: 'agriculture_management.livestock.api.get_flock_financials',
            args: { poultry_flock_id: frm.doc.name },
            callback: function(r) {
                if (r.message) {
                    frm.set_value('total_medication_cost', r.message.total_medication_cost);
                    frm.set_value('total_feed_cost', r.message.total_feed_cost);
                    frm.call('update_financial_metrics');
                }
            }
        });
    },

    refresh_feeding_history: function(frm) {
        agriculture.utils.render_dashboard_grid(frm,
            'agriculture_management.livestock.api.get_group_feeding_history',
            { poultry_flock_id: frm.doc.name },
            'feeding_history',
            { date: 'date', type: 'type', item: 'item', qty: 'qty', record_type: 'record_type', record: 'record' }
        );
    },
    sync_head_count_button: function(frm) {
        frappe.show_alert({ message: __('Syncing with batch stock...'), indicator: 'blue' });

        // Call the new server-side method
        frm.call('sync_head_count_with_batch').then(r => {
            if (r.message) {
                // The server-side function already shows a detailed msgprint.
                // We just need to reload the form to see the updated value.
                frm.reload_doc();
            }
        });
    }
});

// =-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=
// HELPER FUNCTIONS
// =-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=

function render_action_buttons(frm, is_in_withdrawal) {
    // Health and Performance buttons are always available for active flocks
    frm.add_custom_button(__('Group Treatment'), () => { frappe.new_doc('Group Treatment', { livestock_group: frm.doc.livestock_group, is_flock: 1 }); }, __('Health'));
    frm.add_custom_button(__('Group Vaccination'), () => { frappe.new_doc('Group Vaccination', { livestock_group: frm.doc.livestock_group, is_flock: 1 }); }, __('Health'));
    if (frm.doc.flock_type === 'Layer') {
        frm.add_custom_button(__('Record Egg Collection'), () => { frappe.new_doc('Livestock Performance Log', { log_for: 'Poultry Flock', poultry_flock: frm.doc.name, log_type: 'Egg Collection' }); }, __('Performance')).addClass('btn-primary');
    }

    // --- Conditionally add Sales buttons ---
    if (!is_in_withdrawal) {
        if (frm.doc.flock_type === 'Layer') {
            frm.add_custom_button(__('Sell Eggs'), () => {
                let dialog = new frappe.ui.Dialog({
                    title: __("Sell Eggs from Flock"),
                    fields: [
                        {label: 'Customer', fieldname: 'customer', fieldtype: 'Link', options: 'Customer', reqd: 1},
                        {label: 'Egg Item to Sell', fieldname: 'egg_item', fieldtype: 'Link', options: 'Item', reqd: 1, get_query: () => ({ filters: { 'is_stock_item': 1, 'has_batch_no': 1 } })},
                        {label: 'Batch to Sell From', fieldname: 'batch_no', fieldtype: 'Link', options: 'Batch', reqd: 1, get_query: function() { let item = dialog.get_value('egg_item'); if (!item) { frappe.throw(__("Please select an Egg Item first.")); } return { query: 'erpnext.controllers.queries.get_batch_no', filters: { item_code: item, warehouse: frm.doc.coop } }; }},
                        {label: 'Quantity to Sell (Units)', fieldname: 'quantity', fieldtype: 'Float', reqd: 1},
                        {label: 'Rate per Unit', fieldname: 'rate', fieldtype: 'Float', reqd: 1}
                    ],
                    primary_action_label: __('Create Delivery Note'),
                    primary_action: function(values) {
                        frappe.call({ method: 'agriculture_management.livestock.doctype.poultry_flock.poultry_flock.sell_eggs', args: { flock_name: frm.doc.name, sales_details: values }, callback: (r) => { if (r.message) { frm.events.refresh_sales_history(frm); dialog.hide(); } } });
                    }
                });
                dialog.show();
            }, __('Sales')).addClass('btn-primary');
        }
        frm.add_custom_button(__('Sell / Process Flock'), () => {
            let fields = [ { label: 'Customer', fieldname: 'customer', fieldtype: 'Link', options: 'Customer', reqd: 1 }, { label: 'Quantity to Sell', fieldname: 'quantity', fieldtype: 'Int', reqd: 1, default: frm.doc.current_head_count }, { label: 'Rate per Unit', fieldname: 'selling_rate', fieldtype: 'Float', reqd: 1 } ];
            if (frm.doc.flock_type === 'Broiler') {
                fields.push({ label: 'Total Weight of Birds Sold (Kg)', fieldname: 'total_weight_sold', fieldtype: 'Float', reqd: 1, description: 'Required for FCR calculation.' });
            }
            frappe.prompt(fields, (values) => { frappe.call({ doc: frm.doc, method: 'sell_flock', args: values, callback: (r) => { if (r.message) { frm.reload_doc(); } } }); }, __('Sell Flock'));
        }, __('Sales'));
    }
    frm.add_custom_button(__('Process Scheduled Feeding'), () => {
            let dialog = new frappe.ui.Dialog({
                title: __("Process a Scheduled Feeding"),
                fields: [
                    {
                        label: 'Feeding Schedule',
                        fieldname: 'schedule',
                        fieldtype: 'Link',
                        options: 'Feeding Schedule',
                        reqd: 1,
                        get_query: () => {
                            // --- THIS IS THE DEFINITIVE FIX ---
                            // This query now returns only schedules that are:
                            // 1. Linked to the current flock's group.
                            // 2. Are in an active state ('Generated' or 'Partially Completed').
                            // 3. Have not expired (their 'to_date' is today or in the future).
                            return {
                                filters: {
                                    'livestock_group': frm.doc.livestock_group,
                                    'status': ['in', ['Generated', 'Partially Completed']],
                                    'to_date': ['>=', frappe.datetime.now_date()]
                                }
                            };
                            // --- END OF FIX ---
                        }
                    },
                    {
                        label: 'Date to Process',
                        fieldname: 'process_date',
                        fieldtype: 'Date',
                        default: frappe.datetime.now_date(),
                        reqd: 1
                    }
                ],
                primary_action_label: __('Complete Feeding'),
                primary_action: (values) => {
                    // The validation logic for the selected date is now redundant because
                    // the list is pre-filtered, but we can keep it as a double-check.
                    // The function call to process_the_schedule remains the same.
                    process_the_schedule(dialog, values, frm);
                }
            });
            dialog.show();
        }, __('Actions'));
    frm.add_custom_button(__('Record Mortality'), () => {
            frappe.prompt([
                { label: 'Quantity', fieldname: 'quantity', fieldtype: 'Int', reqd: 1 },
                { label: 'Cause', fieldname: 'cause', fieldtype: 'Data' }
            ], (values) => {
                frappe.call({ doc: frm.doc, method: 'record_mortality', args: values, callback: (r) => { if (r.message) { frm.reload_doc(); } } });
            }, __('Record Mortality'));
        }, __('Actions'));

        frm.add_custom_button(__('Record Feeding'), () => {
            frappe.prompt([
                { label: 'Feed Item', fieldname: 'feed_item', fieldtype: 'Link', options: 'Item', reqd: 1 },
                { label: 'Quantity (kg)', fieldname: 'quantity', fieldtype: 'Float', reqd: 1 }
            ], (values) => {
                frappe.call({ doc: frm.doc, method: 'record_feeding', args: values, callback: (r) => { if (r.message) { frm.reload_doc(); } } });
            }, __('Record Feed Consumption'));
        }, __('Actions'));
}

function calculate_and_display_age(frm) {
    if (frm.doc.hatch_date) {
        let age = frappe.datetime.get_diff(frappe.datetime.now_date(), frm.doc.hatch_date);
        if (frm.doc.age_in_days != age) {
            frm.set_value('age_in_days', age);
        }
    } else if (frm.doc.age_in_days) {
        frm.set_value('age_in_days', 0);
    }
}

function process_the_schedule(dialog, values, frm) {
    // This contains the logic that runs after the validation passes.
    frappe.call({
        method: 'agriculture_management.livestock.api.get_planned_feeding_for_date',
        args: {
            schedule_name: values.schedule,
            target_date: values.process_date
        },
        callback: function(r) {
            if (r.message && r.message.name) {
                frappe.model.with_doc("Feeding Schedule", values.schedule, function() {
                    let schedule_doc = frappe.get_doc("Feeding Schedule", values.schedule);
                    frappe.call({
                        doc: schedule_doc,
                        method: "complete_feeding_for_row",
                        args: { row_name: r.message.name },
                        callback: function(res) {
                            if (res.message) {
                                dialog.hide();
                                frappe.show_alert({ message: __("Scheduled feeding completed."), indicator: 'green' });
                                frm.events.refresh_feeding_history(frm);
                            }
                        }
                    });
                });
            } else {
                frappe.throw(__("No 'Planned' feeding found for the selected date on that schedule."));
            }
        }
    });
}