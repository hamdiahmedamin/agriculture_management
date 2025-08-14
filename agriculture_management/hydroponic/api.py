# Final api.py - Corrects the Company AttributeError

import frappe
from frappe.utils import flt
import json

@frappe.whitelist()
def create_bom_from_recipe(recipe_name, dialog_values):
	"""
	API endpoint to create a BOM from a Nutrient Recipe.
	This version correctly sources the Company from the user's default settings.
	"""
	try:
		# Immediately parse the incoming JSON string into a dictionary.
		if isinstance(dialog_values, str):
			dialog_values = json.loads(dialog_values)

		# Get the default group from the custom settings DocType.
		default_group = frappe.db.get_single_value('Hydroponics Settings', 'default_group_for_stock_solutions')
		if not default_group:
			frappe.throw("Please set the 'Default Group for Stock Solutions' in Hydroponics Settings first.")

		recipe = frappe.get_doc('Nutrient Recipe', recipe_name)
		item_name = dialog_values['item_name']

		# Create the Item if it does not exist
		if not frappe.db.exists('Item', item_name):
			finished_item = frappe.new_doc('Item')
			finished_item.item_code = item_name
			finished_item.item_name = item_name
			finished_item.item_group = default_group
			finished_item.stock_uom = dialog_values['uom']
			finished_item.is_stock_item = 1
			finished_item.has_bom = 1
			finished_item.save(ignore_permissions=True)
			frappe.msgprint(f"Created new Item: {finished_item.name}")

		# --- FIX IS HERE ---
		# A BOM must belong to a company. We get it from the user's defaults.
		company = frappe.defaults.get_user_default("company")
		if not company:
			frappe.throw("No default Company found for the current user. Please set one in User Settings.")

		# Create the new BOM document.
		bom = frappe.new_doc('BOM')
		bom.item = item_name
		bom.quantity = flt(dialog_values['batch_size'])
		bom.uom = dialog_values['uom']
		bom.company = company # Assign the fetched company here
		bom.is_active = 1

		# Add ingredients to the BOM
		for ingredient in recipe.ingredients:
			if ingredient.stock_tank_id == dialog_values['stock_tank']:
				required_qty = (flt(ingredient.quantity) / flt(ingredient.base_stock_volume)) * flt(dialog_values['batch_size'])
				bom.append('items', {
					'item_code': ingredient.ingredient,
					'qty': required_qty,
					'uom': ingredient.quantity_uom,
					'source_warehouse': dialog_values['source_warehouse']
				})
		
		if not bom.items:
			frappe.throw(f"No ingredients found in the recipe for Stock Tank <b>{dialog_values['stock_tank']}</b>.")

		bom.insert(ignore_permissions=True)
		
		return {"bom_name": bom.name}

	except Exception as e:
		frappe.log_error(frappe.get_traceback(), 'BOM Creation From Recipe Failed')
		frappe.throw(f"An error occurred during BOM creation: {e}")


@frappe.whitelist()
def get_item_default_warehouse(item_code, company):
	"""
	Safely fetches the default warehouse from an Item's 'Item Default' child table.
	This whitelisted function can be called from the client side.

	:param item_code: The Item Code to look up.
	:param company: The Company to filter the defaults by.
	:return: The default warehouse name, or None if not found.
	"""
	if not item_code or not company:
		return None

	# This is a direct database query that is very efficient.
	# It looks inside the `tabItem Default` table for a matching row.
	warehouse = frappe.db.get_value(
		"Item Default",
		filters={
			"parent": item_code,
			"parenttype": "Item",
			"company": company
		},
		fieldname="default_warehouse"
	)
	
	return warehouse