# Copyright (c) 2025, aminos and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.utils import get_datetime


class DosingLog(Document):
    def on_submit(self):
        """
        This hook runs when the Dosing Log is submitted.
        It creates and submits a 'Material Issue' Stock Entry to consume the dosed items from inventory.
        """
        if self.generated_stock_entry:
            frappe.throw(
                f"A Stock Entry '{self.generated_stock_entry}' has already been generated for this Dosing Log.")

        # Create a new Stock Entry document in memory
        stock_entry = frappe.new_doc("Stock Entry")
        stock_entry.stock_entry_type = "Material Issue"
        stock_entry.company = self.company

        # Use the dosing date as the posting date for accurate records
        stock_entry.posting_date = get_datetime(self.dosing_date).date()
        stock_entry.posting_time = get_datetime(self.dosing_date).time()

        # It's good practice to set a purpose for the stock movement
        stock_entry.purpose = "Material Issue"

        # Link this Stock Entry back to the Dosing Log for traceability
        # Note: You may want to add a custom field "custom_dosing_log" to Stock Entry for this
        # This assumes you created the custom field
        stock_entry.custom_dosing_log = self.name

        # Loop through the items in the Dosing Log's child table
        for item_row in self.dosed_items:
            stock_entry.append("items", {
                "item_code": item_row.item,
                "qty": item_row.quantity_used,
                "uom": item_row.uom,
                "s_warehouse": item_row.source_warehouse,
                # t_warehouse (target) is not needed for Material Issue
                # The expense account is fetched from the item or company default
            })

        # Save the new Stock Entry as a draft
        stock_entry.insert(ignore_permissions=True)
        # Submit the Stock Entry to finalize the stock movement
        stock_entry.submit()

        # Update this Dosing Log with the name of the newly created Stock Entry
        # We use db_set because this document is already submitted and cannot be saved normally.
        self.db_set("generated_stock_entry", stock_entry.name)
        frappe.msgprint(
            f"Stock Entry <a href='/app/stock-entry/{stock_entry.name}'>{stock_entry.name}</a> created successfully.")

    def on_cancel(self):
        """
        This hook runs when the Dosing Log is cancelled.
        It finds the linked Stock Entry and cancels it to reverse the inventory movement.
        """
        if not self.generated_stock_entry:
            return

        try:
            # Load the linked Stock Entry document
            stock_entry = frappe.get_doc(
                "Stock Entry", self.generated_stock_entry)
            if stock_entry.docstatus == 1:  # If it's submitted
                stock_entry.cancel()
                frappe.msgprint(
                    f"Stock Entry {self.generated_stock_entry} has been cancelled.")

            # Clear the link field after cancellation
            self.db_set("generated_stock_entry", None)

        except frappe.DoesNotExistError:
            frappe.msgprint(
                f"Could not find Stock Entry {self.generated_stock_entry} to cancel.")
        except Exception as e:
            frappe.log_error(frappe.get_traceback(),
                             "Dosing Log Stock Cancellation Failed")
            frappe.throw(
                f"Failed to cancel Stock Entry {self.generated_stock_entry}: {str(e)}")
