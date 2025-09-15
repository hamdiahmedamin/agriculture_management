// Copyright (c) 2023, aminos and contributors
// For license information, please see license.txt

frappe.ui.form.on("Water Reservoir", {
	refresh(frm) {
          if (!frm.is_new()) {
            render_dashboard(frm);
              // --- Action Buttons ---
        frm.add_custom_button(__('Refresh Environment'), function() {
            // This function would ideally call an API to get the latest sensor data.
            // For this example, we'll just re-render the dashboard with placeholder data.
            frappe.show_alert({ message: 'Refreshing environmental data...', indicator: 'green' });
            render_dashboard(frm, true); // Pass true to simulate new data
        }, __('Actions'));
            frm.add_custom_button(__('Add Water Quality Reading'), function() {
                // When the button is clicked, open a new form for "Water Quality Reading"
                // and automatically pre-fill the 'water_reservoir' field with the current reservoir's name.
                frappe.new_doc('Water Quality Reading', {
                    water_reservoir: frm.doc.name
                });
            }, __('Actions'));


        }        
            
	},
    water_level_monitoring_system:function(frm){
        if(frm.doc.water_level_monitoring_system=="Other")
            frm.fields_dict.other_water_level_monitoring_system.toggle(true);
        else
            frm.fields_dict.other_water_level_monitoring_system.toggle(false);
    }
});

function render_dashboard(frm) {
    if (frm.is_new()) {
        frm.get_field("dashboard_html").$wrapper.html("");
        return;
    }

    // Show a loading state
    frm.get_field("dashboard_html").$wrapper.html(`<div style="padding: 20px; text-align: center; color: #888;"><p>Loading Latest Reading...</p></div>`);

    // Call the NEW server-side Python function
    frappe.call({
        method: "agriculture_management.hydroponic.doctype.water_reservoir.water_reservoir.get_latest_reading_for_reservoir", // IMPORTANT: Check your app's name
        args: {
            reservoir_name: frm.doc.name // The argument is the name of the current document
        },
        callback: function(r) {
            const data = r.message;
            let dashboard_html;

            if (data) {
                const get_status_color = (value, target, warning_tolerance, critical_tolerance) => {
                    if (target == null || value == null) return '#adb5bd'; // Grey (Neutral)
                    const deviation = Math.abs(value - target);
                    if (deviation <= warning_tolerance) return '#28a745'; // Green (Good)
                    if (deviation <= critical_tolerance) return '#fd7e14'; // Orange (Warning)
                    return '#dc3545'; // Red (Critical)
                };
                
                // Determine colors based on the reservoir's own target fields
                const ph_color = get_status_color(data.ph, frm.doc.target_ph, 0.2, 0.5);
                const ec_color = get_status_color(data.electrical_conductivity, frm.doc.target_ec, 0.3, 0.6);
                const temp_color = get_status_color(data.water_temperature, frm.doc.target_temp, 1.5, 3.0);

                dashboard_html = `
                    <div style="display: grid; grid-template-columns: repeat(auto-fill, minmax(180px, 1fr)); gap: 15px; padding: 15px; background-color: #f7fafc; border-radius: 6px;">
                        <div class="kpi-card" style="padding: 15px; border-radius: 6px; background: white; border-left: 5px solid ${ph_color};">
                            <span style="font-size: 14px; color: #6c757d;">pH Level</span>
                            <h4 style="margin: 5px 0; color: ${ph_color}; font-size: 1.75rem;">${data.ph || 'N/A'}</h4>
                            <small style="color: #6c757d;">Target: ${frm.doc.target_ph || 'N/A'}</small>
                        </div>
                        <div class="kpi-card" style="padding: 15px; border-radius: 6px; background: white; border-left: 5px solid ${ec_color};">
                            <span style="font-size: 14px; color: #6c757d;">EC Level (mS/cm)</span>
                            <h4 style="margin: 5px 0; color: ${ec_color}; font-size: 1.75rem;">${data.electrical_conductivity || 'N/A'}</h4>
                            <small style="color: #6c757d;">Target: ${frm.doc.target_ec || 'N/A'}</small>
                        </div>
                        <div class="kpi-card" style="padding: 15px; border-radius: 6px; background: white; border-left: 5px solid ${temp_color};">
                            <span style="font-size: 14px; color: #6c757d;">Water Temp (°C)</span>
                            <h4 style="margin: 5px 0; color: ${temp_color}; font-size: 1.75rem;">${data.water_temperature || 'N/A'}</h4>
                            <small style="color: #6c757d;">Target: ${frm.doc.target_temp || 'N/A'}</small>
                        </div>
                    </div>
                `;
            } else {
                dashboard_html = `<div style="padding: 20px; text-align: center; color: #888;"><p>No submitted readings found for this reservoir.</p></div>`;
            }

            frm.get_field("dashboard_html").$wrapper.html(dashboard_html);
        }
    });
}