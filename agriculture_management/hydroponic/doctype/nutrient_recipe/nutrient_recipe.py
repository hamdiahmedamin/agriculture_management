# Copyright (c) 2025, aminos and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.utils import flt

class NutrientRecipe(Document):
	"""
	Server-side controller for the Nutrient Recipe DocType.
	Handles validation, automatic calculations, and other backend logic.
	"""
	def validate(self):
		"""
		This method is called before saving. It's used to validate data integrity.
		"""
		if not self.dosing_instructions:
			frappe.throw("Validation Error: You must provide at least one 'Final Reservoir Dosing' instruction.")
		
		self.enforce_ab_separation()

	def before_save(self):
		"""
		This method is called after validate() but before the document is saved to the database.
		Perfect for running calculations and setting field values automatically.
		"""
		self.calculate_total_cost()

	def enforce_ab_separation(self):
		"""
		Prevents incompatible chemicals from being added to the same stock tank.
		Specifically, Calcium Nitrate should not be mixed with Phosphates or Sulfates.
		"""
		tank_contents = {}
		for ingredient in self.ingredients:
			# Initialize the tank list if not present
			if ingredient.stock_tank_id not in tank_contents:
				tank_contents[ingredient.stock_tank_id] = []
			
			# Add the lower-cased ingredient name for case-insensitive checking
			tank_contents[ingredient.stock_tank_id].append(ingredient.ingredient.lower())

		# Check each tank for incompatible combinations
		for tank, contents in tank_contents.items():
			has_calcium = any('calcium' in item for item in contents)
			has_phosphate = any('phosphate' in item for item in contents)
			has_sulfate = any('sulfate' in item for item in contents)

			if has_calcium and (has_phosphate or has_sulfate):
				frappe.throw(
					f"Validation Error: Incompatible chemicals found in Stock Tank <b>{tank}</b>. "
					"Calcium-based ingredients cannot be in the same concentrated stock tank as Phosphates or Sulfates."
				)

	def calculate_total_cost(self):
		"""
		Calculates the total material cost to produce 1000 Liters of the final nutrient solution.
		This method requires a valid Item Price to be set for each ingredient.
		NOTE: This is a simplified calculation and assumes UOM consistency (g, L).
		A more advanced version would use ERPNext's UOM conversion factors.
		"""
		total_cost = 0.0
		
		# Create a mapping of stock tank to its dosing rate in ml per Liter
		dosing_rates_ml_per_l = {
			d.stock_tank: (flt(d.dosing_rate) / flt(d.per_volume_of_water)) 
			for d in self.dosing_instructions
		}

		for ingredient in self.ingredients:
			item_price_rate = frappe.db.get_value('Item Price', {'item_code': ingredient.ingredient, 'selling': 0}, 'price_list_rate')
			
			if not item_price_rate:
				# You could throw an error here, but for now we'll skip to allow saving even if prices aren't set
				continue

			# Get the standard UOM for the item to determine its base unit (e.g., Kg or G)
			item_uom = frappe.db.get_value("Item", ingredient.ingredient, "stock_uom")
			price_per_gram = (flt(item_price_rate) / 1000) if "Kg" in item_uom else flt(item_price_rate)

			# Get the dosing rate for the tank this ingredient belongs to
			rate_ml_per_l_final = dosing_rates_ml_per_l.get(ingredient.stock_tank_id, 0)
			if rate_ml_per_l_final == 0:
				continue

			# Calculate concentration of ingredient in the stock solution (grams per ml)
			concentration_g_per_ml_stock = (flt(ingredient.quantity) / (flt(ingredient.base_volume) * 1000))

			# Calculate cost for 1000L of final solution
			# (price_per_gram) * (grams_per_ml_stock) * (ml_stock_per_L_final) * 1000L
			cost_for_1000L = price_per_gram * concentration_g_per_ml_stock * rate_ml_per_l_final * 1000
			total_cost += cost_for_1000L
		
		self.cost_per_1000l = total_cost