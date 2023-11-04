// Copyright (c) 2017, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on('Weather', {
	/*refresh: (frm) => {
		frm.call('load_contents');
	},*/
	onload: (frm) => {
		if (frm.doc.weather_parameter == undefined) {
			frm.call('load_contents');
			console.log(true);
		}
		console.log(false);
	},
	
	refresh: function (frm) {
		frm.cscript.button_lamf = function (doc) {
			
			if (frm.doc.location == "")
				frappe.msgprint(__('Select Location first'));
			else {
				frm.clear_table("weather_parameter");
				frm.refresh_fields();
				frm.call({
					method: 'load_owm',
					doc: frm.doc,
					args: {},
					freeze: true,
					freeze_message: __('Loading Weather Data.'),
					callback: function(r) {
						frappe.show_alert({
							message:__('Weather Data Loaded.'),
							indicator:'blue'
						}, 5);
					}
				});			
				/* frm.call('set_weather').then(r => {
					if (r.message) {
						frappe.show_alert({
							message:__('Weather Data Loaded.'),
							indicator:'blue'
						}, 5);
					}
				}); */				
			}
		}
	},
	source: function (frm) {
		if (frm.doc.source == "Manual") {
			frm.fields_dict.button_lamf.toggle(false);
			frm.clear_table("weather_parameter");
				frm.refresh_fields();
			frm.call('load_contents');
			console.log("manual");
		} else {
			if (frm.doc.location == "" || frm.doc.location == undefined) {

				frappe.msgprint(__('Select Location first'));
				frm.set_value("source", "Manual");
				frm.clear_table("weather_parameter");
				frm.refresh_fields();
				console.log("location");
			} else {
				frm.fields_dict.button_lamf.toggle(true);
			}
		}
	},
	button_lamf:function(frm){
		
	},
	"location": function (frm) {
		if (frm.doc.location == "") {
			frm.fields_dict.latitude.toggle(false);
			frm.fields_dict.longitude.toggle(false);
		} else {
			frm.fields_dict.latitude.toggle(true);
			frm.fields_dict.longitude.toggle(true);
		}
	},
});