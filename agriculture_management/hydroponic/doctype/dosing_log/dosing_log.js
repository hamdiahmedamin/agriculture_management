/*
* dosing_log.js
* This is the final, complete client script for the Dosing Log form.
* It includes all parent-level filters and visibility, PLUS the new
* cascading filter for Nutrient Batch in the child table.
*/

// --- PARENT DOCTYPE EVENTS ---

frappe.ui.form.on('Dosing Log', {
    /**
     * SETUP: Runs once when the form is initialized.
     */
    setup: function(frm) {
        // This filter correctly applies to the Hydroponic System field.
        frm.set_query('hydroponic_system', function() {
            return {
                filters: {
                    'asset_category': ['in', ['Hydroponic Systems', 'Hydroponic Equipments']], // Corrected to include both
                    'company': frm.doc.company,
                    'status': ['!=', 'Cancelled']
                }
            };
        });
    },

    /**
     * COMPANY (on change): If the company changes, clear dependent fields.
     */
    company: function(frm) {
        frm.set_value('hydroponic_system', null);
        frm.trigger('hydroponic_system'); 
    },

    /**
     * HYDROPONIC SYSTEM (on change): The main trigger for our dynamic UI.
     */
    hydroponic_system: function(frm) {
        if (frm.doc.hydroponic_system) {
            frm.toggle_display('crop_cycle', true);
        } else {
            frm.toggle_display('crop_cycle', false);
        }
        frm.set_value('crop_cycle', null);
        frm.set_query('crop_cycle', function() {
            if (frm.doc.hydroponic_system) {
                return {
                    filters: {
                        'hydroponic_system': frm.doc.hydroponic_system,
                        'status': ['!=', 'Completed']
                    }
                };
            }
            return {};
        });
    },
    
    /**
     * REFRESH: This hook sets the initial state of the form.
     */
    refresh: function(frm) {
        frm.trigger("hydroponic_system");
    }
});


// ##################################################################
// ### NEW LOGIC FOR THE CHILD TABLE ###
// ##################################################################

frappe.ui.form.on('Dosing Log Item', {
    /**
     * This event triggers for each row in the 'dosed_items' child table.
     * We use it to set up the cascading filter for Nutrient Batch.
     */
    dosed_items_add: function(frm, cdt, cdn) {
        set_nutrient_batch_filter(frm, cdt, cdn);
    },
    form_render: function(frm, cdt, cdn) {
        set_nutrient_batch_filter(frm, cdt, cdn);
    },

    /**
     * When the item is changed in a row, clear the old batch selection
     * to force the user to select a new, valid batch.
     */
    item: function(frm, cdt, cdn) {
        frappe.model.set_value(cdt, cdn, 'nutrient_batch', null);
    }
});

/**
 * HELPER function to set the dynamic query on the 'nutrient_batch' field.
 * @param {object} frm - The main form object.
 * @param {string} cdt - The child doctype name ('Dosing Log Item').
 * @param {string} cdn - The child document name (the row's unique ID).
 */
function set_nutrient_batch_filter(frm, cdt, cdn) {
    let grid = frm.get_field('dosed_items').grid;
    // Ensure the grid and row are rendered before getting the field
    if (grid && grid.get_row(cdn)) {
        let field = grid.get_row(cdn).get_field('nutrient_batch');

        field.get_query = function(doc, cdt, cdn) {
            let row = locals[cdt][cdn];
            let item_code = row.item;

            if (!item_code) {
                frappe.throw(__("Please select an Item first to choose a Nutrient Batch."));
            }

            return {
                filters: {
                    'item': item_code,
                    'status': 'Active' // Only show batches that are in stock
                }
            };
        };
    }
}