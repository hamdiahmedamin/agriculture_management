frappe.ui.form.on('Asset', {
    refresh: function(frm) {
        // Only proceed for saved, non-cancelled Hydroponic Systems
       const isHydroponicSystem = frm.doc.asset_category === 'Hydroponic Systems';
        
        if (!isHydroponicSystem || frm.is_new() || frm.doc.docstatus >= 2) {
            // IF it's NOT a Hydroponic System,
            // OR it's a NEW document,
            // OR it's Cancelled,
            // THEN do nothing and exit.
            frm.clear_custom_buttons(); // Also good to clear our buttons if conditions aren't met
            return;
        }

        // --- Server Call to Check for Existing Zones ---
        // This determines which buttons to show.
        frappe.call({
            method: 'agriculture_management.hydroponic.api.check_hydroponic_system_for_zones', // Check your path
            args: { asset_name: frm.doc.name }
        }).then(r => {
            const zone_count = r.message.zone_count || 0;
            
            // Clear previous UI elements to prevent duplication
            frm.clear_custom_buttons();
            if (frm.dashboard && frm.dashboard.clear_indicators) frm.dashboard.clear_indicators();

            if (zone_count > 0) {
                // If zones exist, show a status and a dropdown menu for actions
                frm.dashboard.add_indicator(__('{0} Growing Zones Configured', [zone_count]), 'green');
                frm.add_custom_button(__('Modify Layout'), () => show_layout_dialog(frm), __('Zone Utilities'));
                frm.add_custom_button(__('Delete All Zones'), () => handle_delete_all_zones(frm), __('Zone Utilities'));
            } else {
                // If no zones exist, show a primary button to generate them
                frm.dashboard.add_indicator(__('No Growing Zones Generated'), 'orange');
                frm.add_custom_button(__('Generate Growing Zones'), () => show_layout_dialog(frm)).addClass('btn-primary');
            }
        });
    },

    // --- Triggers for Capacity Calculation ---
    custom_number_of_racks: (frm) => calculate_total_capacity(frm),
    custom_tiers_per_rack: (frm) => calculate_total_capacity(frm),
    custom_gullies_per_tier: (frm) => calculate_total_capacity(frm),
    custom_capacity_per_gully: (frm) => calculate_total_capacity(frm)
});

/**
 * Dialog 1: Collect the desired layout from the user.
 */
function show_layout_dialog(frm) {
    const defaults = {
        naming_prefix: frm.doc.custom_naming_prefix || 'Rack',
        num_racks: frm.doc.custom_number_of_racks || 1,
        num_tiers: frm.doc.custom_tiers_per_rack || 1,
        num_gullies: frm.doc.custom_gullies_per_tier || 1,
        capacity_per_gully: frm.doc.custom_capacity_per_gully || 0
    };

    const dialog = new frappe.ui.Dialog({
        title: __('Define Zone Layout'),
        fields: [
            { label: 'Naming Prefix', fieldname: 'naming_prefix', fieldtype: 'Data', default: defaults.naming_prefix, reqd: 1 },
            { label: 'Number of Racks', fieldname: 'num_racks', fieldtype: 'Int', default: defaults.num_racks, reqd: 1 },
            { label: 'Tiers per Rack', fieldname: 'num_tiers', fieldtype: 'Int', default: defaults.num_tiers, reqd: 1 },
            { label: 'Gullies per Tier', fieldname: 'num_gullies', fieldtype: 'Int', default: defaults.num_gullies, reqd: 1 },
            { label: 'Capacity per Gully', fieldname: 'capacity_per_gully', fieldtype: 'Int', default: defaults.capacity_per_gully, reqd: 1 }
        ],
        primary_action_label: __('Next'),
        primary_action(values) {
            dialog.hide();
            // After getting the layout, ask the user HOW to apply it.
            show_apply_mode_dialog(frm, values);
        }
    });
    dialog.show();
}

/**
 * Dialog 2: Ask the user if they want to 'overwrite' or 'append'.
 */
function show_apply_mode_dialog(frm, layout_values) {
    const dialog = new frappe.ui.Dialog({
        title: __('How should this layout be applied?'),
        fields: [
            {
                fieldname: 'info',
                fieldtype: 'HTML',
                options: `
                    <p>You have defined a new layout. Choose how to apply it:</p>
                    <ul>
                        <li><b>Overwrite:</b> Deletes ALL existing zones and creates a fresh layout. Use this for major changes.</li>
                        <li><b>Append:</b> Keeps all existing zones and only adds the new ones that are missing. Use this for expanding the system.</li>
                    </ul>
                `
            },
            {
                fieldname: 'mode',
                fieldtype: 'Select', // USE 'Select' INSTEAD OF 'Radio'
                label: 'Operation Mode',
                options: [ // Provide options as an array of strings
                    'Append',
                    'Overwrite'
                ],
                default: 'Append', // Append is a safer default
                reqd: 1
            }
        ],
        primary_action_label: __('Apply Changes'),
        primary_action(values) {
            // 'values' will now be an object like { mode: "Overwrite" } or { mode: "Append" }
            // The .toLowerCase() call will now work correctly.
            const mode = values.mode.toLowerCase(); 
            
            dialog.hide();

            if (mode === 'overwrite') {
                frappe.confirm(
                    __('Are you sure you want to permanently delete all existing zones and apply the new layout? This cannot be undone.'),
                    () => {
                        // User confirmed the dangerous action
                        execute_zone_generation(frm, layout_values, mode);
                    },
                    () => {
                        // User cancelled
                        frappe.msgprint(__('Operation Cancelled.'));
                    }
                );
            } else {
                // For the non-destructive 'append' action, proceed directly
                execute_zone_generation(frm, layout_values, mode);
            }
        }
    });
    dialog.show();
}
/**
 * The single function that makes the server call.
 */
function execute_zone_generation(frm, layout_config, mode) {
    frappe.show_progress(__('Processing'), __('Applying new layout...'));
    
    frappe.call({
        method: 'agriculture_management.hydroponic.api.apply_zone_layout_to_asset', // The new, unified server method
        args: {
            asset_name: frm.doc.name,
            layout_config: layout_config, // Pass the whole config object
            mode: mode // Pass the user's choice: 'overwrite' or 'append'
        }
    }).then(r => {
        frappe.hide_progress();
        if (r.message) {
            frappe.show_alert({
                message: __(r.message.message),
                indicator: 'green'
            });
            frm.reload_doc();
        }
    }).catch(err => {
        frappe.hide_progress();
        console.error("Zone Generation Failed.", err);
    });
}

/**
 * Handles the standalone "Delete All Zones" action.
 */
function handle_delete_all_zones(frm) {
    frappe.confirm(
        __('This will permanently delete all Growing Zones linked to this Asset. This action cannot be undone. Are you sure?'),
        () => {
            frappe.call({
                method: 'agriculture_management.hydroponic.api.delete_zones_for_system', // Assumes you have this helper
                args: { asset_name: frm.doc.name }
            }).then(() => {
                frappe.show_alert({ message: __('All zones deleted successfully.'), indicator: 'green' });
                frm.reload_doc();
            });
        }
    );
}

/**
 * Calculates the total plant capacity based on the layout fields.
 */
function calculate_total_capacity(frm) {
    const racks = frm.doc.custom_number_of_racks || 0;
    const tiers = frm.doc.custom_tiers_per_rack || 0;
    const gullies = frm.doc.custom_gullies_per_tier || 0;
    const capacity = frm.doc.custom_capacity_per_gully || 0;
    frm.set_value('custom_plant_capacity', racks * tiers * gullies * capacity);
}