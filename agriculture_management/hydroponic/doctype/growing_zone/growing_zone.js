// Copyright (c) 2025, aminos and contributors
// For license information, please see license.txt

// Copyright (c) 2025, aminos and contributors
// For license information, please see license.txt

frappe.ui.form.on('Growing Zone', {
    refresh: function(frm) {
        // Render the live dashboard as the first thing
        render_dashboard(frm);

        if (frm.is_new()) {
            return; // Don't show buttons or history on a new, unsaved document
        }

        // --- Action Buttons ---
        frm.add_custom_button(__('Refresh Environment'), function() {
            // This function would ideally call an API to get the latest sensor data.
            // For this example, we'll just re-render the dashboard with placeholder data.
            frappe.show_alert({ message: 'Refreshing environmental data...', indicator: 'green' });
            render_dashboard(frm, true); // Pass true to simulate new data
        }, __('Actions'));

        // --- History Buttons ---
        frm.add_custom_button(__('View Maintenance History'), function() {
            frappe.set_route('List', 'Asset Maintenance', {
                'asset': frm.doc.hydroponic_system // Assuming maintenance is linked to the parent asset
            });
        }, __('History'));

        frm.add_custom_button(__('View Yield History'), function() {
            frappe.set_route('List', 'Harvest Log', {
                'growing_zone': frm.doc.name
            });
        }, __('History'));
    }
});

function render_dashboard(frm) {
    // Don't try to render if the document is new and hasn't been saved yet
    if (frm.is_new()) {
        frm.get_field("dashboard_html").$wrapper.html(""); // Clear any previous dashboard
        return;
    }

    // Show a loading state
    frm.get_field("dashboard_html").$wrapper.html(`
        <div style="padding: 20px; text-align: center; color: #888;">
            <p>Loading Latest Environmental Data...</p>
        </div>
    `);

    // Call the server-side Python function to get real data
    frappe.call({
        method: "agriculture_management.hydroponic.doctype.growing_zone.growing_zone.get_latest_environmental_reading", // IMPORTANT: Check your app's name
        args: {
            zone_name: frm.doc.name
        },
        callback: function(r) {
            const data = r.message;
            let dashboard_html;

            if (data) {
                /**
                 * NEW: A more advanced function to determine status color.
                 * It returns a specific color code based on how far the value
                 * deviates from the target.
                 * - Green: Within safe limits.
                 * - Orange: Warning, needs attention.
                 * - Red: Critical, needs immediate action.
                 */
                const get_status_color = (value, target, warning_tolerance, critical_tolerance) => {
                    if (target == null || value == null) return '#adb5bd'; // Grey (Neutral)
                    
                    const deviation = Math.abs(value - target);
                    if (deviation <= warning_tolerance) return '#28a745'; // Green (Good)
                    if (deviation <= critical_tolerance) return '#fd7e14'; // Orange (Warning)
                    return '#dc3545'; // Red (Critical)
                };
                
                // Determine the color for each metric based on its deviation from the target
                const ph_color = get_status_color(data.ph, frm.doc.target_ph, 0.2, 0.5);
                const ec_color = get_status_color(data.electrical_conductivity, frm.doc.target_ec, 0.3, 0.6);
                
                // For temperature, we can add a default target if not specified in the DocType
                const temp_color = get_status_color(data.water_temperature, frm.doc.target_water_temperature, 1.5, 3.0);


                dashboard_html = `
                    <div style="display: grid; grid-template-columns: repeat(auto-fill, minmax(180px, 1fr)); gap: 15px; padding: 15px; background-color: #f7fafc; border-radius: 6px;">
                        
                        <!-- pH KPI Card -->
                        <div class="kpi-card" style="padding: 15px; border-radius: 6px; background: white; border-left: 5px solid ${ph_color};">
                            <span style="font-size: 14px; color: #6c757d;">pH Level</span>
                            <h4 style="margin: 5px 0; color: ${ph_color}; font-size: 1.75rem;">${data.ph || 'N/A'}</h4>
                            <small style="color: #6c757d;">Target: ${frm.doc.target_ph || 'N/A'}</small>
                        </div>
                        
                        <!-- EC KPI Card -->
                        <div class="kpi-card" style="padding: 15px; border-radius: 6px; background: white; border-left: 5px solid ${ec_color};">
                            <span style="font-size: 14px; color: #6c757d;">EC Level (mS/cm)</span>
                            <h4 style="margin: 5px 0; color: ${ec_color}; font-size: 1.75rem;">${data.electrical_conductivity || 'N/A'}</h4>
                            <small style="color: #6c757d;">Target: ${frm.doc.target_ec || 'N/A'}</small>
                        </div>
                        
                        <!-- Temperature KPI Card -->
                        <div class="kpi-card" style="padding: 15px; border-radius: 6px; background: white; border-left: 5px solid ${temp_color};">
                            <span style="font-size: 14px; color: #6c757d;">Water Temp (°C)</span>
                            <h4 style="margin: 5px 0; color: ${temp_color}; font-size: 1.75rem;">${data.water_temperature || 'N/A'}</h4>
                            
                             <small style="color: #6c757d;">Target: ${frm.doc.target_water_temperature || 'N/A'}</small>
                        </div>

                    </div>
                `;
            } else {
                // No data was found, show a clear message
                dashboard_html = `
                    <div style="padding: 20px; text-align: center; color: #888;">
                        <p>No environmental readings found for this zone's reservoir.</p>
                        <p>Please log a reading in the parent system's Water Reservoir.</p>
                    </div>
                `;
            }

            frm.get_field("dashboard_html").$wrapper.html(dashboard_html);
        }
    });
}