/*
* propagation_log.js
* Adds automation and dynamic filters to the Propagation Log form.
* This is the complete and final version.
*/
frappe.ui.form.on('Propagation Log', {
    /**
     * ONLOAD: This event is the best place to set up filters that
     * should be active for the life of the form.
     */
    onload: function(frm) {
        // Filter the 'seed_item' field to only show items from the 'Seeds' group.
        frm.set_query('seed_item', function() {
            return {
                filters: {
                    'item_group': 'Seeds'
                }
            };
        });

        // Filter the 'source_warehouse' field based on the selected company.
        frm.set_query('source_warehouse', function() {
            return {
                filters: {
                    'company': frm.doc.company
                }
            };
        });
        frm.set_query('consumable_batch', function() {
            return {
                filters: {
                    'consumable_type': 'Seeds'
                }
            };
        });
    },

    /**
     * COMPANY (on change): When the company changes, clear the warehouse
     * to force the user to select a new, valid one.
     */
    company: function(frm) {
        frm.set_value('source_warehouse', null);
    },

    /**
     * SEED ITEM (on change): When the seed item is selected, securely fetch
     * its linked Crop via a whitelisted server call.
     */
    seed_item: function(frm) {
        if (frm.doc.seed_item) {
            // Call our whitelisted Python function to get data securely
            frappe.call({
                method: "agriculture_management.agriculture.doctype.propagation_log.propagation_log.get_crop_for_seed_item",
                args: {
                    item_code: frm.doc.seed_item
                },
                callback: function(r) {
                    // The 'r.message' contains the return value from our Python function
                    if (r && r.message) {
                        frm.set_value('crop', r.message);
                    } else {
                        frm.set_value('crop', null); // Clear the field if no crop is found
                    }
                }
            });
        } else {
            frm.set_value('crop', null); // Clear the field if the seed item is cleared
        }
    },

    /**
     * When any of the date or duration fields change, recalculate the schedule.
     */
    sowing_date: function(frm) {
        calculate_dates(frm);
    },
    expected_germination_days: function(frm) {
        calculate_dates(frm);
    },
    days_to_transplant_ready: function(frm) {
        calculate_dates(frm);
    },

    /**
     * When the number of germinated seedlings is entered, calculate the success rate.
     */
    quantity_germinated: function(frm) {
        if (frm.doc.quantity_seeded && frm.doc.quantity_germinated) {
            if (parseFloat(frm.doc.quantity_germinated) > parseFloat(frm.doc.quantity_seeded)) {
                frappe.msgprint(__("Quantity Germinated cannot be greater than Quantity Seeded."));
                frm.set_value('quantity_germinated', frm.doc.quantity_seeded);
            }
            let rate = (frm.doc.quantity_germinated / frm.doc.quantity_seeded) * 100;
            frm.set_value('germination_rate', rate);
        } else {
            frm.set_value('germination_rate', 0); // Reset if values are missing
        }
    },

    /**
     * REFRESH: Add the "Create Planting Schedule" button for submitted documents.
     */
    refresh: function(frm) {
        frm.remove_custom_button('Create Planting Schedule');
        if (frm.doc.docstatus === 1 && frm.doc.status === 'Ready for Transplant') {
            frm.add_custom_button(__('Create Planting Schedule'), function() {
                create_planting_schedule(frm);
            }).addClass('btn-primary');
        }
    }
});

// --- HELPER FUNCTIONS ---

/**
 * Calculates the expected dates for germination and transplanting.
 * @param {object} frm - The current form object.
 */
function calculate_dates(frm) {
    if (frm.doc.sowing_date) {
        if (frm.doc.expected_germination_days) {
            let germ_date = frappe.datetime.add_days(frm.doc.sowing_date, frm.doc.expected_germination_days);
            frm.set_value('expected_germination_date', germ_date);

            // The 'transplant ready' days are added to the NEW germination date
            if (frm.doc.days_to_transplant_ready) {
                let trans_date = frappe.datetime.add_days(germ_date, frm.doc.days_to_transplant_ready);
                frm.set_value('expected_transplant_date', trans_date);
            }
        } else {
            // Clear dates if the duration is cleared
            frm.set_value('expected_germination_date', null);
            frm.set_value('expected_transplant_date', null);
        }
    }
}

/**
 * Creates a new Planting Schedule, pre-filling it with data from this log.
 * @param {object} frm - The current form object.
 */
function create_planting_schedule(frm) {
    frappe.new_doc('Planting Schedule', {
        crop: frm.doc.crop,
        quantity_to_plant: frm.doc.quantity_germinated,
        target_planting_date: frm.doc.expected_transplant_date,
        company: frm.doc.company,
        linked_propagation_log: frm.doc.name
    });
}