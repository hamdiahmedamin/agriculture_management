/* eslint-disable */
// Client-side script for Crop Cycle

frappe.ui.form.on('Crop Cycle', {
    // ========================================================================
    // INITIALIZATION & SETUP
    // ========================================================================
    setup: function(frm) {
        // Dynamic filter for hydroponic_system
        frm.set_query('hydroponic_system', function() {
            return {
                filters: {
                    'asset_category': 'Hydroponic Systems'
                }
            };
        });
    },

    onload: function(frm) {
        // Default Naming Series on new doc
        if (frm.is_new() && !frm.doc.naming_series) {
            frm.trigger("growth_method");
        }

        // Add company filter to hydroponic system query
        frm.set_query('hydroponic_system', function() {
            return {
                filters: {
                    'asset_category': 'Hydroponic Systems',
                    'status': ['!=', 'Cancelled'],
                    'company': frm.doc.company
                }
            };
        });
        
        // Dynamic filter for cost_center
        frm.set_query("cost_center", () => {
			return {
				filters: {
					company: frm.doc.company,
                    is_group: 0,
				},
			};
		});

        // Pre-filling logic from localStorage
        if (frm.is_new() && localStorage.getItem('new_crop_cycle_data')) {
            var data_string = localStorage.getItem('new_crop_cycle_data');
            localStorage.removeItem('new_crop_cycle_data');
            try {
                var prefill_data = JSON.parse(data_string);
                function set_if_exists(fieldname, value) {
                    if (frm.fields_dict[fieldname] && value) {
                        frm.set_value(fieldname, value);
                    }
                }
                set_if_exists('crop', prefill_data.crop);
                set_if_exists('start_date', prefill_data.start_date);
                set_if_exists('end_date', prefill_data.end_date);
                set_if_exists('status', prefill_data.status);
                set_if_exists('company', prefill_data.company);
                set_if_exists('linked_planting_schedule', prefill_data.linked_planting_schedule);
                set_if_exists('growth_method', prefill_data.growth_method);
                set_if_exists('hydroponic_system', prefill_data.hydroponic_system);
                set_if_exists('location', prefill_data.location);
                if ($.isArray(prefill_data.growing_zones) && prefill_data.growing_zones.length > 0) {
                    if (frm.fields_dict['growing_zones']) {
                        frm.clear_table('growing_zones');
                        prefill_data.growing_zones.forEach(function(zone_data) {
                            var new_row = frm.add_child('growing_zones');
                            new_row.growing_zone = zone_data.growing_zone;
                        });
                        frm.refresh_field('growing_zones');
                    }
                }
            } catch (e) { console.error("Error during form pre-fill:", e); }
        }
    },

    // ========================================================================
    // REFRESH & BUTTONS
    // ========================================================================
    refresh: function(frm) {
        // --- SECTION 1: BUTTONS ---
        frm.clear_custom_buttons(); // Always clear first
        
        // This button group will hold all our custom actions
        const actions_group_label = __("Actions");

        if (!frm.is_new()) {            
            // Add buttons for saved documents to the group
             // Make it the main button
            frm.add_custom_button(__('Update Dashboard'), function() {
                frm.call('update_dashboard_totals').then(function() {
                    frm.refresh_fields();
                    frappe.show_alert({message: __('Dashboard totals have been updated.'), indicator: 'green'});
                });
            }, actions_group_label);

            frm.add_custom_button(__('Record New Harvest'), function() {
                frappe.new_doc("Harvest Log", {
                    crop_cycle: frm.doc.name,
                    company: frm.doc.company
                });
            }, actions_group_label);
            frm.add_custom_button(__('Create Harvest Entry'), function() {
            // This now launches the new, powerful Harvest Entry form.
            frappe.new_doc("Harvest Entry", {
                // It automatically links this Crop Cycle, saving the user a step.
                crop_cycle: frm.doc.name
            });
        }, actions_group_label);
        frm.add_custom_button(__('Refresh Harvest Summary'), () => {
            frappe.show_alert({message: __('Reloading harvest data...'), indicator: 'grey'});

            // Call the new Python method
            frm.call('reload_harvest_summary').then(() => {
                // This runs after the server is done.
                // We just need to refresh the child table field to show the new data.
                frm.refresh_field('harvest_log');
            });
        }, actions_group_label);
            
            frm.add_custom_button(__('Reload Linked Analysis'), () => {
                frm.call('reload_linked_analysis').then(() => {
                    frm.refresh(); 
                });
            }, actions_group_label);
        }

        // --- SECTION 2: DYNAMIC ZONE MANAGEMENT LOGIC ---
        // This function will add the "Load" or "Generate" button to the primary button area
        // It only runs if the growth method is Hydroponic
        if (frm.doc.growth_method === 'Hydroponic') {
            setup_zone_buttons(frm);
        }

        // --- SECTION 3: RENDER PEST & DISEASE LOG LIST ---
        if (!frm.is_new()) {
            render_pest_log(frm);
        }
    },

    // ========================================================================
    // FIELD TRIGGERS
    // ========================================================================
    growth_method: function(frm) {
        if (frm.is_new()) {
            frm.set_value('naming_series', frm.doc.growth_method === 'Hydroponic' ? 'HCC-.YYYY.-' : 'CC-.YYYY.-');
        }
    },
    
    hydroponic_system: function(frm) {
        // Clear the child table and setup buttons when the system is changed
        frm.clear_table('growing_zones');
        frm.refresh_field('growing_zones');
        setup_zone_buttons(frm);
    },
    
    // Automatic calculation triggers
    number_of_lines: function(frm) { calculate_total_plants(frm); },
    plants_per_line: function(frm) { calculate_total_plants(frm); },
    number_of_rows: function(frm) { calculate_total_plants(frm); },
    number_of_harvests: function(frm) { calculate_total_duration(frm); },
    cycle_duration: function(frm) { calculate_total_duration(frm); }
});

// ========================================================================
// HELPER FUNCTIONS
// ========================================================================

/**
 * Checks if the selected Hydroponic System has zones and displays
 * the appropriate button ("Load" or "Generate").
 * @param {object} frm - The current form object.
 */
function setup_zone_buttons(frm) {
    // Clear previous versions of these specific buttons
    frm.remove_custom_button(__('Generate Growing Zones'));
    frm.remove_custom_button(__('Load All Growing Zones'));

    if (!frm.doc.hydroponic_system) {
        return;
    }

    frappe.call({
        method: 'agriculture_management.hydroponic.api.check_hydroponic_system_for_zones',
        args: { asset_name: frm.doc.hydroponic_system },
        callback: function(r) {
            if (r.message) {
                if (r.message.has_zones) {
                    frm.add_custom_button(__('Load All Growing Zones'), function() {
                        load_zones(frm);
                    }).addClass('btn-primary');
                } else {
                    frm.add_custom_button(__('Generate Growing Zones'), function() {
                        generate_zones(frm);
                    }).addClass('btn-primary');
                }
            }
        }
    });
}

/**
 * Fetches and populates the 'growing_zones' child table.
 * @param {object} frm - The current form object.
 */
function load_zones(frm) {
    frappe.show_alert({message: __('Loading zones...'), indicator: 'grey'});
    frappe.call({
        method: 'agriculture_management.hydroponic.api.get_zones_for_system',
        args: { asset_name: frm.doc.hydroponic_system },
        callback: function(r) {
            if (r.message && r.message.length > 0) {
                frm.clear_table('growing_zones');
                r.message.forEach(zone => {
                    frm.add_child('growing_zones', zone);
                });
                frm.refresh_field('growing_zones');
                frappe.msgprint(`${r.message.length} growing zones loaded successfully.`);
            }
        }
    });
}

/**
 * Opens a dialog to generate zones and then loads them.
 * @param {object} frm - The current form object.
 */
function generate_zones(frm) {
    let d = new frappe.ui.Dialog({
        title: __('Generate Growing Zones'),
        fields: [
            { label: 'Naming Prefix', fieldname: 'naming_prefix', fieldtype: 'Data', default: 'Rack', reqd: 1 },
            { label: 'Number of Racks', fieldname: 'num_racks', fieldtype: 'Int', reqd: 1, default: 1 },
            { label: 'Tiers per Rack', fieldname: 'num_tiers', fieldtype: 'Int', reqd: 1, default: 1 },
            { label: 'Gullies per Tier', fieldname: 'num_gullies', fieldtype: 'Int', reqd: 1, default: 1 },
            { label: 'Capacity per Gully', fieldname: 'capacity_per_gully', fieldtype: 'Int', reqd: 1 }
        ],
        primary_action_label: __('Generate'),
        primary_action(values) {
            frappe.show_alert({message: __('Generating zones...'), indicator: 'grey'});
            values.asset_name = frm.doc.hydroponic_system;
            frappe.call({
                method: 'agriculture_management.hydroponic.api.generate_growing_zones',
                args: values,
                callback: function(r) {
                    d.hide();
                    load_zones(frm); // Automatically load after generating
                }
            });
        }
    });
    d.show();
}

/**
 * Renders the Pest and Disease Log as a dynamic list in an HTML field.
 * @param {object} frm - The current form object.
 */
function render_pest_log(frm) {
    var wrapper = frm.get_field("pest_and_disease_log_list").$wrapper;
    wrapper.html('<div>Loading Incident Logs...</div>');
    frappe.db.get_list("Pest and Disease Log", {
        filters: { crop_cycle: frm.doc.name },
        fields: ["name", "log_date", "pest_or_disease", "severity", "status"],
        order_by: "log_date desc"
    }).then(function(logs) {
        var html = `<div class="d-flex justify-content-between align-items-center mb-3">
                        <h4>Incidents</h4>
                        <button class="btn btn-primary btn-sm btn-add-log">Add Pest and Disease Log</button>
                    </div>`;
        if (logs && logs.length > 0) {
            html += '<ul class="list-group">';
            logs.forEach(function(log) {
                var severity_color = 'secondary';
                if (log.severity === 'Low') { severity_color = 'info'; }
                else if (log.severity === 'Medium') { severity_color = 'warning'; }
                else if (log.severity === 'High' || log.severity === 'Critical') { severity_color = 'danger'; }
                html += `<a href="/app/pest-and-disease-log/${log.name}" 
                           class="list-group-item list-group-item-action" 
                           style="border-left: 5px solid var(--bs-${severity_color}) !important;">
                            <div class="d-flex w-100 justify-content-between">
                                <h6 class="mb-1">${log.pest_or_disease}</h6>
                                <small>${frappe.datetime.str_to_user(log.log_date)}</small>
                            </div>
                            <p class="mb-1">
                                Severity: <span class="badge bg-${severity_color}">${log.severity}</span> | Status: ${log.status}
                            </p>
                            <small class="text-muted">${log.name}</small>
                        </a>`;
            });
            html += '</ul>';
        } else {
            html += `<div class="text-muted p-4 text-center">
                        No Pest or Disease Logs recorded for this Crop Cycle.
                    </div>`;
        }
        wrapper.html(html);
        wrapper.find('.btn-add-log').on('click', function() {
            frappe.new_doc("Pest and Disease Log", {
                crop_cycle: frm.doc.name
            });
        });
    });
}

/**
 * Calculates the total number of plants in the system.
 * @param {object} frm - The current form object.
 */
function calculate_total_plants(frm) {
    let total = 0;
    if (frm.doc.number_of_lines > 0 && frm.doc.plants_per_line > 0 && frm.doc.number_of_rows > 0) {
        total = frm.doc.number_of_lines * frm.doc.plants_per_line * frm.doc.number_of_rows;
    }
    frm.set_value('total_plants', total);
}

/**
 * Calculates the total duration for all harvests.
 * @param {object} frm - The current form object.
 */
function calculate_total_duration(frm) {
    let total = 0;
    if (frm.doc.number_of_harvests > 0 && frm.doc.cycle_duration > 0) {
        total = frm.doc.number_of_harvests * frm.doc.cycle_duration;
    }
    frm.set_value('total_duration', total);
}