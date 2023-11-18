// Copyright (c) 2023, aminos and contributors
// For license information, please see license.txt

frappe.ui.form.on("Water Reservoir", {
	refresh(frm) {
        
            
	},
    water_level_monitoring_system:function(frm){
        if(frm.doc.water_level_monitoring_system=="Other")
            frm.fields_dict.other_water_level_monitoring_system.toggle(true);
        else
            frm.fields_dict.other_water_level_monitoring_system.toggle(false);
    }
});
