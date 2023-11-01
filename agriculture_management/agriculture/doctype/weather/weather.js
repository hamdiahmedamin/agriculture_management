// Copyright (c) 2017, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on('Weather', {
	/*refresh: (frm) => {
		frm.call('load_contents');
	},*/
	onload: (frm) => {
		if (frm.doc.weather_parameter == undefined){
			frm.call('set_weather');
			console.log(true);	
		}
		console.log(false);		
	},
	refresh: function(frm){
		cur_frm.cscript.button_lamf = function(doc) {
			//frm.doc.weather_parameter=[];
			//frm.get_field('weather_parameter').grid.grid_rows[0].remove();
			/* var tbl = frm.doc.weather_parameter;
			console.log(tbl.length);
			for(var i = 0; i < tbl.length; i++)
			{
			console.log(frm.get_field('weather_parameter').grid.grid_rows[i]);
			frm.get_field('weather_parameter').grid.grid_rows[i].remove();
			
			}
			//frm.refresh() */
			frm.call('set_weather');
			frappe.msgprint(__('Document updated successfully'));
			}
	}
});