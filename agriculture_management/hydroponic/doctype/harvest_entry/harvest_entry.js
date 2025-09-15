// Copyright (c) 2025, aminos and contributors
// For license information, please see license.txt
frappe.ui.form.on('Harvest Entry', {
    refresh: function(frm) {       
        frm.fields_dict["zones_harvested"].grid.get_field("growing_zone").get_query = function(doc, cdt, cdn) {
            return {
                filters: {
                    current_crop_cycle: frm.doc.crop_cycle
                }
            };
        };    
        toggle_zones_table(frm);
         if (frm.doc.docstatus === 0 && frm.doc.crop_cycle) {
            frm.get_field('zones_harvested').grid.add_custom_button(__('Add Zones by Range'), () => {
                
                // Call 1: Get the layout of the system to build the dialog fields
                frappe.call({
                    method: "agriculture_management.hydroponic.doctype.harvest_entry.harvest_entry.get_system_layout_details", // Check your app name!
                    args: { crop_cycle: frm.doc.crop_cycle },
                    callback: function(r) {
                        const layout = r.message;
                        if (!layout) return; // Error is thrown by the server if no layout

                        // THIS IS THE FIX: Use new frappe.ui.Dialog for older versions
                        const dialog = new frappe.ui.Dialog({
                            title: __('Select Zones by Structure'),
                            fields: [
                                {
                                    fieldname: 'rack_num',
                                    fieldtype: 'Select',
                                    label: __('Rack Number'),
                                    options: Array.from({ length: layout.racks }, (_, i) => i + 1), // Generate options [1, 2, ..., n]
                                    reqd: 1
                                },
                                {
                                    fieldname: 'tier_num',
                                    fieldtype: 'Select',
                                    label: __('Tier Number'),
                                    options: Array.from({ length: layout.tiers }, (_, i) => i + 1),
                                    reqd: 1
                                },
                                {
                                    fieldtype: 'Column Break'
                                },
                                {
                                    fieldname: 'gully_start',
                                    fieldtype: 'Int',
                                    label: __('From Gully'),
                                    default: 1,
                                    reqd: 1
                                },
                                {
                                    fieldname: 'gully_end',
                                    fieldtype: 'Int',
                                    label: __('To Gully'),
                                    default: layout.gullies, // Pre-fill with max gullies
                                    reqd: 1
                                }
                            ],
                            primary_action_label: __('Find and Add Zones'),
                            primary_action(values) {
                                // Basic validation
                                if (values.gully_start > values.gully_end) {
                                    frappe.msgprint(__('"From Gully" cannot be greater than "To Gully".'));
                                    return;
                                }

                                const existing_zones = (frm.doc.zones_harvested || []).map(row => row.growing_zone).filter(Boolean);
                                frappe.show_progress(__('Searching'), __('Finding matching zones...'));

                                // Call 2: Get the actual zone names based on the user's selection
                                frappe.call({
                                    method: "agriculture_management.hydroponic.doctype.harvest_entry.harvest_entry.get_zones_by_structure", // Check app name!
                                    args: {
                                        crop_cycle: frm.doc.crop_cycle,
                                        rack_num: values.rack_num,
                                        tier_num: values.tier_num,
                                        gully_start: values.gully_start,
                                        gully_end: values.gully_end,
                                        existing_zones: JSON.stringify(existing_zones)
                                    },
                                    callback: function(res) {
                                        frappe.hide_progress();
                                        const matching_zones = res.message;

                                        if (!matching_zones || matching_zones.length === 0) {
                                            frappe.show_alert({
                                                message: __('No available zones found for the selected range.'),
                                                indicator: 'orange'
                                            });
                                            return;
                                        }

                                        // Add the found zones to the child table
                                        matching_zones.forEach(zone => {
                                            frm.add_child('zones_harvested', {
                                                growing_zone: zone
                                            });
                                        });
                                        frm.refresh_field('zones_harvested');
                                        frappe.show_alert({
                                            message: __(`${matching_zones.length} zones added.`),
                                            indicator: 'green'
                                        });
                                        dialog.hide();
                                    }
                                });
                            }
                        });
                        dialog.show();
                    }
                });
            });
        }
    },
    crop_cycle: function(frm) {
        toggle_zones_table(frm);
    }
});
function toggle_zones_table(frm) {
    if (frm.doc.crop_cycle) {
        frm.toggle_enable("zones_harvested", true);
    } else {
        frm.toggle_enable("zones_harvested", false);
    }
}
// Real-time calculation of totals
frappe.ui.form.on('Harvest Entry Zone', {
    // When the table is changed (rows added/removed)
    zones_harvested_remove: function(frm) {
        calculate_totals(frm);
    },
    // When a value within a row is changed
    quantity_harvested: function(frm) {
        calculate_totals(frm);
    },
    waste_weight: function(frm) {
        calculate_totals(frm);
    }
});

function calculate_totals(frm) {
    let total_qty = 0;
    let total_waste = 0;

    // Loop through each row in the 'zones_harvested' table
    (frm.doc.zones_harvested || []).forEach(function(row) {
        total_qty += row.quantity_harvested || 0;
        total_waste += row.waste_weight || 0;
    });

    // Set the calculated values in the parent document's fields
    frm.set_value('total_quantity_harvested', total_qty);
    frm.set_value('total_waste', total_waste);
    frm.refresh_field('total_quantity_harvested');
    frm.refresh_field('total_waste');
}