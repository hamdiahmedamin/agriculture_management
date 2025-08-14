# Copyright (c) 2025, aminos and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.utils import flt

class SanitizationLog(Document):
	def before_submit(self):
		"""
		Validation now checks if the child table is empty.
		"""
		if not self.chemicals_used:
			frappe.throw("You must add at least one chemical to the 'Chemicals Used' table before submitting.")
		
		# You could add more validation here, e.g., checking if any row has a quantity of 0.
		for chemical_row in self.chemicals_used:
			if not flt(chemical_row.quantity_used) > 0:
				frappe.throw(f"Row #{chemical_row.idx}: 'Quantity Used' must be greater than 0.")


	def on_submit(self):
		"""
		The logic is updated to handle the child table.
		"""
		try:
			se_name = self.create_material_issue_entry()
			frappe.db.set_value("Sanitization Log", self.name, "generated_stock_entry", se_name)
			frappe.msgprint(f"Successfully deducted consumables via Stock Entry: <a href='/app/stock-entry/{se_name}'>{se_name}</a>")
		except Exception as e:
			frappe.log_error(frappe.get_traceback(), "Sanitization Log Stock Deduction Failed")
			frappe.throw(f"Could not create Stock Entry. Error: {e}")

	def on_cancel(self):
		"""This logic remains the same."""
		if self.generated_stock_entry:
			try:
				stock_entry_doc = frappe.get_doc("Stock Entry", self.generated_stock_entry)
				if stock_entry_doc.docstatus == 1:
					stock_entry_doc.cancel()
					frappe.msgprint(f"Cancelled linked Stock Entry: {self.generated_stock_entry}")
			except frappe.DoesNotExistError:
				pass
		frappe.db.set_value("Sanitization Log", self.name, "generated_stock_entry", "")


	# --- Helper Method (Updated) ---
	
	def create_material_issue_entry(self):
		"""
		This method is now updated to loop through the child table.
		"""
		# Use the company from the first row's warehouse to set the company for the whole transaction.
		first_warehouse = self.chemicals_used[0].source_warehouse
		company = frappe.db.get_value("Warehouse", first_warehouse, "company")
		if not company:
			frappe.throw("Could not determine Company from the warehouse in the first row.")

		se = frappe.new_doc("Stock Entry")
		se.stock_entry_type = "Material Issue"
		se.set("purpose", "Material Issue")
		se.company = company
		
		# --- THE CORE LOGIC CHANGE ---
		# Loop through the 'chemicals_used' table in this document.
		for chemical in self.chemicals_used:
			valuation_rate = frappe.db.get_value("Item", chemical.sanitizing_agent, "valuation_rate") or 0
			
			# Append each chemical as a new row in the Stock Entry's 'items' table.
			se.append("items", {
				"item_code": chemical.sanitizing_agent,
				"qty": chemical.quantity_used,
				"uom": chemical.uom,
				"s_warehouse": chemical.source_warehouse,
				"basic_rate": valuation_rate,
				"valuation_rate": valuation_rate,
			})
		
		se.insert(ignore_permissions=True)
		se.submit()

		return se.name