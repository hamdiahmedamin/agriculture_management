// Copyright (c) 2025, aminos and contributors
// For license information, please see license.txt

frappe.ui.form.on('Livestock Group', {
    setup: function(frm) {
        // --- Filters for Link Fields ---
        frm.set_query('animal', 'animal_list', function(doc) {
            if (!doc.species) { frappe.throw(__('Please select a Species for the group first.')); }
            return { filters: { 'species': doc.species } };
        });
        frm.set_query('group_type', function(doc) {
            if (!doc.main_group_type) { frappe.throw(__('Please select a Main Group Type first.')); }
            return { filters: { 'main_group_type': doc.main_group_type } };
        });
        frm.set_query('cost_center', function(doc) { 
            return { filters: { 'company': doc.company, 'is_group': 0 } };
        });
        frm.set_query('group_location', function(doc) { 
            return { filters: { 'company': doc.company, 'is_group': 0 } };
        });
    },

    refresh: function(frm) {
        frm.clear_custom_buttons();
        frm.original_species = frm.doc.species;

        if (!frm.is_new()) {
            // --- Conditional Button Logic ---
            if (frm.doc.is_flock) {
                frm.add_custom_button(__('Synchronize with Flock'), function() {
                    if (!frm.doc.poultry_flock) {
                        frappe.msgprint({ title: __('Action Needed'), indicator: 'orange', message: __('Please select a Poultry Flock to synchronize with.') });
                        return;
                    }
                    frm.call('sync_with_poultry_flock').then(() => {
                        frm.reload_doc();
                    });
                }, __('Actions')).addClass('btn-primary');
            } else { // Not a flock
                frm.add_custom_button(__('Refresh Animal Stats'), function() {
                    // This button saves the document, which correctly triggers the
                    // automatic 'before_save' recalculation.
                    if (frm.is_dirty()) {
                        frappe.msgprint({ title: __('Action Needed'), indicator: 'orange', message: __('Please save your changes to refresh statistics.') });
                    } else {
                        frappe.show_alert({ message: __('Refreshing...'), indicator: 'blue' });
                        frm.save().then(() => {
                             frappe.show_alert({ message: __('Statistics have been refreshed and saved.'), indicator: 'green' });
                        });
                    }
                }, __('Actions')).addClass('btn-primary');

                frm.add_custom_button(__('Record Direct Feed'), () => {
                    // --- THIS IS THE DEFINITIVE, SMART DIALOG ---
                    // First, fetch the default warehouse from Livestock Settings.
                    frappe.db.get_single_value("Livestock Settings", "default_feed_warehouse")
                        .then(default_warehouse => {
                            let dialog = new frappe.ui.Dialog({
                                title: __("Record Direct Feed"),
                                fields: [
                                    {
                                        label: 'Feed Item', fieldname: 'feed_item',
                                        fieldtype: 'Link', options: 'Item', reqd: 1,
                                        get_query: () => ({ filters: { 'is_stock_item': 1 } })
                                    },
                                    {
                                        label: 'Source Warehouse', fieldname: 'source_warehouse',
                                        fieldtype: 'Link', options: 'Warehouse', reqd: 1,
                                        // The field is pre-filled with the default value.
                                        default: default_warehouse,
                                        get_query: function() {
                                            let item = dialog.get_value('feed_item');
                                            if (!item) { frappe.throw(__("Please select a Feed Item first.")); }
                                            return {
                                                query: "erpnext.controllers.queries.get_warehouse_with_stock",
                                                filters: { "item_code": item }
                                            };
                                        }
                                    },
                                    {
                                        label: 'Total Quantity Consumed (Kg)', fieldname: 'quantity',
                                        fieldtype: 'Float', reqd: 1
                                    }
                                ],
                                primary_action_label: __('Record Feeding'),
                                primary_action: (values) => {
                                    frm.call('record_direct_feed', {
                                        feed_item: values.feed_item,
                                        quantity: values.quantity,
                                        source_warehouse: values.source_warehouse
                                    }).then(() => {
                                        dialog.hide();
                                    });
                                }
                            });
                            dialog.show();
                        });
                }, __('Actions'));
            }
        }
    },
    
    main_group_type: function(frm) {
        frm.set_value('group_type', '');
    },

    is_flock: function(frm) {
        frm.refresh();
    },

    company: function(frm) {
        frm.set_value('cost_center', null);
        frm.set_value('group_location', null);
    },

    species: function(frm) {
        if (frm.doc.species !== frm.original_species && frm.doc.animal_list && frm.doc.animal_list.length > 0) {
            frappe.confirm(
                __('Changing the species will clear the Animal List. Are you sure?'),
                () => {
                    frm.clear_table('animal_list');
                    frm.refresh_field('animal_list');
                    frm.original_species = frm.doc.species;
                },
                () => {
                    frm.set_value('species', frm.original_species);
                }
            );
        } else {
            frm.original_species = frm.doc.species;
        }
    }
});

frappe.ui.form.on('Animal List', {
    // --- Duplicate Prevention Logic ---
    before_animal_list_add: function(frm, cdt, cdn) {
        let row = locals[cdt][cdn];
        row.validating = true;
    },
    animal: function(frm, cdt, cdn) {
        let row = locals[cdt][cdn];
        if (row.validating) {
            row.validating = false;
            return;
        }
        let existing_animals = (frm.doc.animal_list || [])
            .filter(d => d.name !== cdn)
            .map(d => d.animal);
        if (existing_animals.includes(row.animal)) {
            frappe.msgprint(__("Animal '{0}' is already in this group. Please select a different animal.", [row.animal]));
            frappe.model.set_value(cdt, cdn, 'animal', '');
        }
    }
});