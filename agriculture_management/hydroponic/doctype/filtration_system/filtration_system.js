// Copyright (c) 2023, aminos and contributors
// For license information, please see license.txt

frappe.ui.form.on("Filtration System", {
 setup: function(frm) {
        // --- THIS IS THE FIX ---
        // We now filter for both categories.
        frm.set_query('linked_asset', function() {
            return { 
                filters: { 
                    'asset_category': ['in', ['Hydroponic Systems', 'Hydroponic Equipments']] ,
                    'status': ['!=', 'Cancelled']
                } 
            };
        });
        // ... rest of your setup function
    },
});
