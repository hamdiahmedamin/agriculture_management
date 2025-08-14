/* eslint-disable */
// Client-side script for Nutrient Recipe DocType

frappe.ui.form.on('Nutrient Recipe', {
	refresh: function(frm) {
		// Only show the button if the document is saved and has ingredients
		if (!frm.is_new() && frm.doc.ingredients && frm.doc.ingredients.length > 0) {
			frm.add_custom_button(__('Generate BOM'), function() {
				generate_bom_dialog(frm);
			}, __('ERPNext Integration'));
		}
	}
});

function generate_bom_dialog(frm) {
	// Get unique stock tank IDs from the ingredients table to populate the dropdown
	const stock_tanks = [...new Set(frm.doc.ingredients.map(item => item.stock_tank_id))];

	let dialog = new frappe.ui.Dialog({
		title: __('Generate BOM for Stock Solution'),
		fields: [
			{
				label: 'Stock Tank to Produce',
				fieldname: 'stock_tank',
				fieldtype: 'Select',
				options: stock_tanks,
				reqd: 1
			},
			{
				label: 'Finished Good Item Name',
				fieldname: 'item_name',
				fieldtype: 'Data',
				description: 'This will be the name of the final manufactured stock solution item.',
				reqd: 1
			},
			{
				label: 'Batch Size (Quantity to Make)',
				fieldname: 'batch_size',
				fieldtype: 'Float',
				description: 'e.g., The total Liters of stock solution to produce.',
				reqd: 1
			},
			{
				label: 'Unit of Measure',
				fieldname: 'uom',
				fieldtype: 'Link',
				options: 'UOM',
				default: frm.doc.ingredients[0].base_volume_uom, // Sensible default
				reqd: 1
			},
			{
				label: 'Raw Material Warehouse',
				fieldname: 'source_warehouse',
				fieldtype: 'Link',
				options: 'Warehouse',
                get_query: function() {
                    return {
                        filters: {
                            'company': frm.doc.company
                        }
                    }
                },
				reqd: 1
			}
		],
		primary_action_label: __('Create BOM'),
		primary_action(values) {
			frappe.show_alert({ message: __('Creating BOM...'), indicator: 'blue' });

			// Call the server-side python function via the API
			frappe.call({
				method: 'agriculture_management.hydroponic.api.create_bom_from_recipe', // IMPORTANT: Change 'your_custom_app'
				args: {
					recipe_name: frm.doc.name,
					dialog_values: values
				},
				callback: function(r) {
					if (r.message) {
						// Success! Show a confirmation message with a link to the new BOM.
						frappe.msgprint({
							title: __('Success'),
							message: __('Successfully created BOM: {0}', [`<a href="/app/bom/${r.message.bom_name}" class="strong">${r.message.bom_name}</a>`]),
							indicator: 'green'
						});
						// Optionally, link the new BOM in the recipe form
						frm.set_value('related_bom', r.message.bom_name);
						dialog.hide();
					}
				}
			});
		}
	});

	// A nice UX touch: suggest a name for the finished good item when the tank is selected
	dialog.fields_dict.stock_tank.df.onchange = () => {
		const values = dialog.get_values();
		if (values.stock_tank) {
			const suggested_name = `Stock Solution ${values.stock_tank} - ${frm.doc.recipe_name}`;
			dialog.set_value('item_name', suggested_name);
		}
	};

	dialog.show();
}