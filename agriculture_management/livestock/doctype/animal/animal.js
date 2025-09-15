// =================================================================
// CLIENT SCRIPT for Animal DocType (Definitive Final Version)
// =================================================================
frappe.ui.form.on('Animal', {

    setup: function (frm) {
        // --- Filters for Link Fields (Run once on setup) ---
        frm.set_query('dam_mother', () => ({ filters: { 'gender': 'Female', 'status': 'Active', 'name': ['!=', frm.doc.name] } }));
        frm.set_query('sire_father', () => ({ filters: { 'gender': 'Male', 'status': 'Active', 'name': ['!=', frm.doc.name] } }));
         frm.set_query('livestock_group', function(doc) {
            // This function runs every time the user clicks the 'livestock_group' field.
            if (!doc.species) {
                frappe.throw(__("Please select a Species for the animal before assigning it to a group."));
            }
            // Return a filter object to the link field pop-up.
            // It will only show groups where the 'species' field matches the animal's species.
            return {
                filters: {
                    'species': doc.species
                }
            };
        });
    },
    species: function(frm) {
        // If the user changes the species, the old group might be invalid.
        // Clear it to force them to re-select a valid group.
        if (frm.doc.livestock_group) {
            frm.set_value('livestock_group', '');
            frappe.msgprint(__("The Livestock Group has been cleared because the Species was changed. Please select a new, valid group."));
        }
    },
    onload: function (frm) {
        // --- Calculate and display the human-readable age on initial load ---
        // This is the safest place to set an initial calculated value.
        calculate_and_display_age(frm);
    },

    refresh: function (frm) {
        // This function orchestrates all UI updates that need to happen on every refresh.

        // --- 1. Basic UI Setup ---
        if (frm.is_new()) {
            frm.toggle_display(['health_log_tab', 'breeding_tab', 'genealogy_tab'], false);
        } else {
            frm.toggle_display(['health_log_tab', 'breeding_tab', 'genealogy_tab'], true);
        }

        frm.clear_custom_buttons();
        if (frm.is_new()) { return; }

       



        if (frm.doc.status === 'In Withdrawal') {
            // If in withdrawal, show the alert and DO NOT add any action buttons.
            frm.dashboard.set_headline_alert(
                `<strong>Warning: In Withdrawal Period until ${frappe.datetime.str_to_user(frm.doc.in_withdrawal_until)}</strong>. No actions are permitted.`,
                'red'
            );
        } else {
            // If not in withdrawal, render the normal buttons.
            render_action_buttons(frm);
            render_inventory_buttons(frm);
        }

    },

    date_of_birth: function (frm) {
        // Provide instant feedback when the user changes the date.
        calculate_and_display_age(frm);
    },
    refresh_health_history: function(frm) {
        agriculture.utils.render_dashboard_grid(
            frm,
            'agriculture_management.livestock.api.get_animal_health_history',
            { animal_id: frm.doc.name },
            'health_history', // Fieldname of the new table
            { // Field Map
                date: 'date',
                event_type: 'event_type',
                details: 'details',
                status: 'status',
                record_type: 'record_type',
                record: 'record'
            }
        );},
        refresh_breeding_history: function(frm) {
                agriculture.utils.render_dashboard_grid(
                    frm,
                    'agriculture_management.livestock.api.get_breeding_history_for_animal',
                    { animal_id: frm.doc.name },
                    'breeding_history', // Fieldname of the table
                    { // Field Map
                        mate: 'mate',
                        breeding_date: 'breeding_date',
                        expected_due_date: 'expected_due_date',
                        outcome: 'outcome',
                        offspring: 'offspring',
                        birth_date: 'birth_date',
                        name: 'breeding_event'
                    }
                );},
        refresh_offspring_list: function(frm) {
            agriculture.utils.render_dashboard_grid(
                frm,
                'agriculture_management.livestock.api.get_offspring_and_mates',
                { animal_id: frm.doc.name },
                'offspring_list', // Fieldname of the table
                { // Field Map
                    offspring: 'offspring',
                    mate: 'mate',
                    date_of_birth: 'date_of_birth',
                    gender: 'gender'
                }
            ); 
        },
        refresh_feeding_history: function(frm) {
        // This calls the new API and uses the global helper to populate the grid
        agriculture.utils.render_dashboard_grid(
            frm,
            'agriculture_management.livestock.api.get_animal_feeding_history',
            { animal_id: frm.doc.name },
            'animal_feeding_log', // The fieldname of the child table
            { // The field map
                date: 'date',
                description: 'description',
                quantity_consumed_est: 'quantity_consumed_est',
                source_doctype: 'source_doctype',
                source_document: 'source_document'
            }
        );
    },
});

// =-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=
// HELPER FUNCTIONS
// =-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=

function render_action_buttons(frm) {
    // --- Breeding Button ---
    if (frm.doc.status === 'Active') {
        frm.add_custom_button(__('Direct Feed'), () => {
            // Fetch the default warehouse from Livestock Settings first
            frappe.db.get_single_value("Livestock Settings", "default_feed_warehouse")
                .then(default_warehouse => {
                    let dialog = new frappe.ui.Dialog({
                        title: __("Record Direct Feed for {0}", [frm.doc.animal_name]),
                        fields: [
                            {label: 'Feed Item', fieldname: 'feed_item', fieldtype: 'Link', options: 'Item', reqd: 1},
                            {label: 'Source Warehouse', fieldname: 'source_warehouse', fieldtype: 'Link', options: 'Warehouse', default: default_warehouse, reqd: 1},
                            {label: 'Quantity Consumed (Kg)', fieldname: 'quantity', fieldtype: 'Float', reqd: 1}
                        ],
                        primary_action_label: __('Record Feeding'),
                        primary_action: (values) => {
                            // Call the new method on the Animal document
                            frm.call('record_direct_feed', {
                                feed_item: values.feed_item,
                                quantity: values.quantity,
                                source_warehouse: values.source_warehouse
                            }).then(() => {
                                dialog.hide();
                                // Refresh the history to show the new entry
                                frm.events.refresh_feeding_history(frm);
                            });
                        }
                    });
                    dialog.show();
                });
        }, __('Create'));
        frm.add_custom_button(__('Breeding Event'), () => {
            let prefill = (frm.doc.gender === 'Female') ? { 'dam': frm.doc.name } : { 'sire': frm.doc.name };
            frappe.new_doc('Breeding Event', prefill);
        }, __('Create')); // Grouped under "Create"
    }

    // --- Health Buttons ---
    if (['Active', 'Quarantined'].includes(frm.doc.status)) {
        frm.add_custom_button(
            __('Treatment Record'),
            () => frappe.new_doc('Treatment Record', {
                animal: frm.doc.name
            }),
            __('Create'));

        frm.add_custom_button(
            __('Vaccination Record'),
            () => frappe.new_doc('Vaccination Record', { animal: frm.doc.name }), __('Create'));
    }
}

function render_inventory_buttons(frm) {
    if (frm.doc.is_serialized_item) {
        if (!frm.doc.serial_no) {
            // SCENARIO 1: No Serial No exists yet.
            frm.add_custom_button(__('Create Serial No'), () => {
                frappe.call({
                    method: 'agriculture_management.livestock.api.create_serial_no_for_animal',
                    args: { animal_doc_name: frm.doc.name },
                    callback: (r) => {
                        if (r.message) {
                            frm.set_value('serial_no', r.message);
                            frm.save();
                        }
                    }
                });
            }, __('Inventory')); // Grouped under "Inventory"

        } else {
            // SCENARIO 2: Serial No exists. Check its stock status asynchronously.
            frappe.db.get_value("Serial No", frm.doc.serial_no, "warehouse").then(r => {
                let in_stock = r.message && r.message.warehouse;

                if (!in_stock) {
                    // --- THE DEFINITIVE FIX ---
                    // 2a: Not in stock. Show the single button to do everything.
                    frm.add_custom_button(__('Receive into Stock'), () => {

                        frappe.confirm('This will create and submit a Stock Receipt in the background. Are you sure?', () => {
                            // Call our new, all-in-one server function
                            frappe.call({
                                method: "agriculture_management.livestock.api.create_and_submit_stock_receipt",
                                args: {
                                    animal_doc_name: frm.doc.name
                                },
                                callback: function (res) {
                                    if (res.message) {
                                        // The server did everything. We just need to set the link and save.
                                        frm.set_value('stock_receipt_entry', res.message);
                                        frm.save();
                                    }
                                }
                            });
                        });

                    }, __('Inventory'));
                } else if (in_stock && !frm.doc.stock_receipt_entry) {
                    // 2b: In stock, but not linked. Show link button.
                    frm.add_custom_button(__('Link Stock Receipt'), () => {
                        frappe.call({
                            method: "agriculture_management.livestock.api.get_stock_entry_for_serial_no",
                            args: { serial_no: frm.doc.serial_no },
                            callback: (res) => {
                                if (res.message) {
                                    frm.set_value('stock_receipt_entry', res.message);
                                    frm.save();
                                }
                            }
                        });
                    }, __('Inventory'));
                } else if (frm.doc.stock_receipt_entry) {
                    // SCENARIO 3: Already linked. Show the "Unlink" button.
                    frm.add_custom_button(__('Unlink Stock Entry'), () => {
                        frappe.confirm(
                            __('Are you sure you want to unlink the Stock Entry?'),
                            () => {
                                frm.set_value('stock_receipt_entry', null);
                                frm.save();
                            }
                        );
                    }, __('Inventory')).addClass('btn-danger');
                }
            });
        }
    }
}

function calculate_and_display_age(frm) {
    if (frm.doc.date_of_birth) {
        frappe.call({
            method: "agriculture_management.livestock.api.get_human_readable_age",
            args: { birth_date_str: frm.doc.date_of_birth },
            callback: (r) => {
                if (r.message && frm.doc.age_display !== r.message) {
                    frm.set_value('age_display', r.message);
                }
            }
        });
    } else if (frm.doc.age_display) {
        frm.set_value('age_display', '');
    }
}

