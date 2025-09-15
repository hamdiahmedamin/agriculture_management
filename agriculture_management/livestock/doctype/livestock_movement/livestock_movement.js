// Copyright (c) 2025, aminos and contributors
// For license information, please see license.txt

// =================================================================
// CLIENT SCRIPT for Livestock Movement
// =================================================================
frappe.ui.form.on('Livestock Movement', {
    // This trigger runs when the 'movement_type' field is changed.
    movement_type: function(frm) {
        // Clear all relevant fields when the type is changed to prevent confusion.
        frm.set_value('animal', null);
        frm.set_value('livestock_group', null);
        frm.set_value('from_location', null);
    },

    // Runs when the 'animal' field is selected.
    animal: function(frm) {
        if (frm.doc.animal) {
            frappe.db.get_value('Animal', frm.doc.animal, 'location_pen')
                .then(r => {
                    if (r.message) {
                        frm.set_value('from_location', r.message.location_pen);
                    }
                });
        }
    },

    // Runs when the 'livestock_group' field is selected.
    livestock_group: function(frm) {
        if (frm.doc.livestock_group) {
            frappe.db.get_value('Livestock Group', frm.doc.livestock_group, 'group_location')
                .then(r => {
                    if (r.message) {
                        frm.set_value('from_location', r.message.group_location);
                    }
                });
        }
    }
});