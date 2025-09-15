// Copyright (c) 2025, aminos and contributors
// For license information, please see license.txt

/*
* nutrient_batch.js
* Handles pre-filling from Purchase Receipt and adds intelligent filters.
*/
frappe.ui.form.on('Consumable Batch', {
    /**
     * ONLOAD: This is the main event for setting up the form.
     */
    onload: function(frm) {
        
        // --- LOGIC TO PRE-FILL FROM PURCHASE RECEIPT ---
        // This runs only when a new document is being created.
        if (frm.is_new()) {
            // Check if our data exists in local storage.
            let data_string = localStorage.getItem('new_nutrient_batch_data');
            
            if (data_string) {
                // IMPORTANT: Immediately clear the data so it's only used once.
                localStorage.removeItem('new_nutrient_batch_data');

                try {
                    // Decode the JSON string back into an array of item objects.
                    let items_data = JSON.parse(data_string);
                    
                    // For now, we will pre-fill with the data from the FIRST item in the receipt.
                    // A more advanced version could create multiple batches at once.
                    if (items_data && items_data.length > 0) {
                        let first_item = items_data[0];
                        
                        // Set the values on the form.
                        frm.set_value('item', first_item.item);
                        frm.set_value('quantity_received', first_item.quantity_received);
                        frm.set_value('warehouse', first_item.warehouse);
                        frm.set_value('company', first_item.company);
                        frm.set_value('supplier', first_item.supplier);

                        frappe.show_alert({
                            message: __('Pre-filled data from Purchase Receipt. Please enter Supplier Lot No. and Expiry Date.'),
                            indicator: 'green'
                        });
                    }
                } catch (e) {
                    console.error("Failed to parse or pre-fill from Purchase Receipt data.", e);
                }
            }
        }

        // --- FILTERING LOGIC (from our previous discussion) ---
        frm.set_query('item', function() {
            return { filters: { 'item_group': frm.doc.consumable_type} };
        });

        frm.set_query('warehouse', function() {
            return { filters: { 'company': frm.doc.company } };
        });
    },

    /**
     * COMPANY (on change): Clear the dependent warehouse field.
     */
    company: function(frm) {
        frm.set_value('warehouse', null);
    }
});