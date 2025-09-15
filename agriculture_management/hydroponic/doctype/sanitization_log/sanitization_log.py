# Copyright (c) 2025, aminos and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.utils import flt


class SanitizationLog(Document):
    def before_submit(self):
        """
        This validation runs before the document is submitted.
        We can add a check here to ensure quantities are positive if items are entered.
        """
        for chemical_row in self.chemicals_used:
            if not flt(chemical_row.quantity_used) > 0:
                frappe.throw(
                    f"Row #{chemical_row.idx}: 'Quantity Used' must be greater than 0 if you add an item.")

    def on_submit(self):
        """
        This hook now intelligently creates a Stock Entry ONLY if chemicals were used.
        """
        # --- THIS IS THE CRUCIAL NEW LOGIC ---
        # Check if the 'chemicals_used' child table is not empty.
        if self.chemicals_used:
            try:
                # If there are chemicals, proceed with creating the Stock Entry.
                se_name = self.create_material_issue_entry()
                # Use db_set for submitted documents.
                frappe.db.set_value(
                    "Sanitization Log", self.name, "generated_stock_entry", se_name)
                frappe.msgprint(
                    f"Successfully deducted consumables via Stock Entry: <a href='/app/stock-entry/{se_name}' target='_blank'>{se_name}</a>")
            except Exception as e:
                frappe.log_error(frappe.get_traceback(),
                                 "Sanitization Log Stock Deduction Failed")
                frappe.throw(f"Could not create Stock Entry. Error: {e}")
        else:
            # If the table is empty, do nothing and inform the user.
            frappe.msgprint(
                "No chemicals were used in this log. No Stock Entry was created.", indicator="blue")
        # --- END OF NEW LOGIC ---

    def on_cancel(self):
        """This logic remains the same and will only run if a stock entry exists."""
        if self.generated_stock_entry:
            try:
                stock_entry_doc = frappe.get_doc(
                    "Stock Entry", self.generated_stock_entry)
                if stock_entry_doc.docstatus == 1:
                    stock_entry_doc.cancel()
                    frappe.msgprint(
                        f"Cancelled linked Stock Entry: {self.generated_stock_entry}")
            except frappe.DoesNotExistError:
                # If the entry is not found, we don't need to do anything.
                pass
            # Clear the field regardless of whether the cancellation was needed.
            frappe.db.set_value("Sanitization Log", self.name,
                                "generated_stock_entry", "")

    # --- Helper Method (Your existing logic is good) ---

    def create_material_issue_entry(self):
        """
        This helper method creates the Material Issue document.
        """
        # This assumes you have added a 'company' field to your Sanitization Log DocType.
        if not self.company:
            frappe.throw(
                "Cannot create Stock Entry: <b>Company</b> is a required field.")

        se = frappe.new_doc("Stock Entry")
        se.stock_entry_type = "Material Issue"
        se.set("purpose", "Material Issue")
        se.company = self.company
        se.posting_date = self.sanitization_date

        # Loop through the 'chemicals_used' table.
        for chemical in self.chemicals_used:
            # Append each chemical as a new row in the Stock Entry's 'items' table.
            se.append("items", {
                "item_code": chemical.sanitizing_agent,
                "qty": chemical.quantity_used,
                "uom": chemical.uom,
                "s_warehouse": chemical.source_warehouse,
                # valuation_rate will be fetched automatically by ERPNext on submit.
            })

        se.insert(ignore_permissions=True)
        se.submit()

        return se.name
