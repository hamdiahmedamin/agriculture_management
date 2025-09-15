frappe.ui.form.on('Soil Analysis', {
    /**
     * ONLOAD: Auto-load the criteria table if it's a new document.
     */
    onload: function(frm) {
        if (frm.is_new() && !frm.doc.soil_analysis_criteria.length) {
            frm.call('load_contents');
        }
    },

    refresh: function(frm) {
        // Add a button to manually trigger the ratio calculation
        if (!frm.is_new()) {
            frm.add_custom_button(__('Recalculate Ratios'), () => {
                // Call the python method and then refresh the form to see the new values
                frm.call('recalculate_ratios').then(() => {
                    frm.refresh_fields();
                });
            });
        }
    },

    /**
     * CROP CYCLE (on change): Fetches context data.
     */
    crop_cycle: function(frm) {
        frm.set_value('company', null);
        frm.set_value('land_unit', null);

        if (frm.doc.crop_cycle) {
            // Re-use our secure, whitelisted API function
            frappe.call({
                method: "agriculture_management.agriculture.api.get_log_context",
                args: { crop_cycle_name: frm.doc.crop_cycle },
                callback: function(r) {
                    if (r && r.message) {
                        frm.set_value('company', r.message.company);
                        frm.set_value('land_unit', r.message.land_unit);
                    }
                }
            });
        }
    }
});