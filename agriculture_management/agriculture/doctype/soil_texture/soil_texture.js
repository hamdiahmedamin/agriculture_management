/*
* soil_texture.js
* This is the definitive, final client script. It uses the explicit 'run_doc_method'
* via frappe.call to bypass the framework bug and fix the 'AttributeError'.
*/
frappe.provide('agriculture');

let is_balancing = false;

frappe.ui.form.on('Soil Texture', {
	refresh: (frm) => {
		let map_tools = ["a.leaflet-draw-draw-polyline",
			"a.leaflet-draw-draw-polygon",
			"a.leaflet-draw-draw-rectangle",
			"a.leaflet-draw-draw-circle",
			"a.leaflet-draw-draw-circlemarker"];

		map_tools.forEach((element) => $(element).hide());
        // Initialize or redraw the plot
		draw_or_refresh_plot(frm);
	},
	onload: function(frm) {
		if (!frm.doc.soil_texture_criteria || frm.doc.soil_texture_criteria.length === 0) {
			frm.call('load_contents');
		}
	},
    crop_cycle: function(frm) {
        frm.set_value('company', null);
        frm.set_value('land_unit', null);
        if (frm.doc.crop_cycle) {
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
    },

	clay_composition: function(frm) {
        handle_composition_change(frm);
    },
    sand_composition: function(frm) {
        handle_composition_change(frm);
    },
    silt_composition: function(frm) {
        handle_composition_change(frm);
    }
});
function handle_composition_change(frm) {
    // If we are already in the middle of balancing, do nothing to prevent loops.
    if (is_balancing) return;

    // 1. Balance the percentages on the client-side.
    balance_percentages(frm);

    // 2. Call the server to get the calculated soil type.
    call_server_for_soil_type(frm);
    
    // 3. Redraw the plot with the new, balanced values.
    draw_or_refresh_plot(frm);
}

/**
 * HELPER: This function performs the instant, client-side balancing.
 */
function balance_percentages(frm) {
    is_balancing = true; // Set the flag to prevent other events from firing

    const fields = ['clay_composition', 'sand_composition', 'silt_composition'];
    let values = {};
    let defined_fields = [];
    
    // Read current values and count how many have been entered by the user
    fields.forEach(f => {
        let val = flt(frm.doc[f]);
        values[f] = val;
        // Consider a field "defined" if it has a value.
        if (val > 0 || frm.doc[f] === 0) { // Check for explicit 0 as well
            defined_fields.push(f);
        }
    });

    // Only proceed if exactly two of the three fields have been entered
    if (defined_fields.length === 2) {
        let total_of_two = values[defined_fields[0]] + values[defined_fields[1]];
        
        // If the two values are valid (don't already exceed 100)
        if (total_of_two <= 100) {
            // Find the name of the third, empty field
            let third_field = fields.find(f => !defined_fields.includes(f));
            
            // Calculate the remainder and set it in the third field
            let remainder = 100 - total_of_two;
            frm.set_value(third_field, remainder);
        }
    }
    
    // Unset the flag so the script can run again on the next user action
    is_balancing = false;
}

/**
 * HELPER FUNCTION: This contains the definitive frappe.call syntax.
 */
function call_server_for_soil_type(frm) {
    let total = Math.round(flt(frm.doc.clay_composition) + flt(frm.doc.sand_composition) + flt(frm.doc.silt_composition));
    
    // Only call the server if the total is exactly 100
    if (total !== 100) {
        frm.set_value('soil_type', 'Select'); // Reset if not 100
        return;
    }

    let data_to_send = {
        clay_composition: frm.doc.clay_composition,
        sand_composition: frm.doc.sand_composition,
        silt_composition: frm.doc.silt_composition
    };

    frappe.call({
        method: 'agriculture_management.agriculture.doctype.soil_texture.soil_texture.get_soil_type_from_composition',
        args: { data: data_to_send },
        callback: function(r) {
            if (r && r.message) {
                frm.set_value('soil_type', r.message);
            }
        }
    });
}
/**
 * HELPER: This function draws or updates the plot.
 */
function draw_or_refresh_plot(frm) {
    if (!frm.ternary_plot_instance) {
		try {
			frm.ternary_plot_instance = new agriculture.TernaryPlot({
				parent: frm.get_field("ternary_plot").$wrapper,
				clay: frm.doc.clay_composition,
				sand: frm.doc.sand_composition,
				silt: frm.doc.silt_composition,
			});
		} catch(e) {
			console.error("Failed to create TernaryPlot.", e);
		}
	} else {
        // If the plot already exists, just update the data point.
        frm.ternary_plot_instance.remove_blip();
        frm.ternary_plot_instance.mark_blip({
            clay: frm.doc.clay_composition, 
            sand: frm.doc.sand_composition, 
            silt: frm.doc.silt_composition
        });
    }
}