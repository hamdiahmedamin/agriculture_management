// Copyright (c) 2025, aminos and contributors
// For license information, please see license.txt
// =================================================================
// CLIENT SCRIPT for Breeding Event
// =================================================================
frappe.ui.form.on('Breeding Event', {

    setup: function(frm) {
        // --- Filters for Dam, Sire, and Offspring ---
        frm.set_query('dam', () => ({ filters: { 'gender': 'Female', 'status': 'Active' } }));
        frm.set_query('sire', () => ({ filters: { 'gender': 'Male', 'status': 'Active' } }));
        frm.set_query('offspring', (doc) => ({ filters: [['Animal', 'name', 'not in', [doc.dam, doc.sire]]] }));
    },

    // When the Dam is selected, fetch her data to populate other fields.
    dam: function(frm) {
        if (frm.doc.dam) {
            // Fetch multiple fields (species and breed) in a single call for efficiency.
            frappe.db.get_value('Animal', frm.doc.dam, ['species', 'breed'])
                .then(r => {
                    let values = r.message;
                    if (values) {
                        // Set the fetched values and refresh the fields.
                        frm.set_value('species', values.species);
                        frm.set_value('breed', values.breed);
                        
                        // Trigger the due date calculation if a breeding date already exists.
                        if (frm.doc.breeding_date) {
                            frm.trigger("breeding_date");
                        }
                    }
                });
        } else {
            // If Dam is cleared, clear the dependent fields.
            frm.set_value('species', '');
            frm.set_value('breed', '');
        }
    },
    refresh: function(frm) {
        // --- THIS IS THE NEW, DYNAMIC READ-ONLY LOGIC ---
        
        // Check if an offspring has been generated and linked.
        if (frm.doc.offspring) {
            // If yes, lock the critical fields to make the record immutable.
            frm.set_df_property('outcome', 'read_only', 1);
            frm.set_df_property('offspring_id', 'read_only', 1);
            frm.set_df_property('offspring_gender', 'read_only', 1);
            frm.set_df_property('birth_date', 'read_only', 1);
            frm.set_df_property('health_status', 'read_only', 1);
        } else {
            // If no offspring is linked, ensure the fields are editable.
            // This is important for when a user might cancel/amend the document.
            frm.set_df_property('outcome', 'read_only', 0);
            frm.set_df_property('offspring_id', 'read_only', 0);
            frm.set_df_property('offspring_gender', 'read_only', 0);
            frm.set_df_property('birth_date', 'read_only', 0);
            frm.set_df_property('health_status', 'read_only', 0);
        }
        
        // Refresh the form layout to apply the read-only changes immediately.
        frm.refresh_fields();
    }
});