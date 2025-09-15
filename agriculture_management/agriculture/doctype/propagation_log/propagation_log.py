# Copyright (c) 2025, aminos and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.utils import getdate


class PropagationLog(Document):
    def on_submit(self):
        """
        This hook runs when the Propagation Log is submitted.
        It creates and submits a 'Material Issue' Stock Entry to consume the
        seeds from inventory.
        """
        if self.generated_stock_entry:
            frappe.throw(
                f"A Stock Entry '{self.generated_stock_entry}' has already been generated for this log.")

        if not self.seed_item or not self.quantity_seeded > 0:
            frappe.msgprint(
                "No seeds were used in this log. No Stock Entry will be created.")
            return

        # Create a new Stock Entry document in memory
        stock_entry = frappe.new_doc("Stock Entry")
        stock_entry.stock_entry_type = "Material Issue"
        stock_entry.company = self.company

        # Use the sowing date as the posting date for accurate stock records
        stock_entry.posting_date = self.sowing_date

        # It's good practice to set a purpose for the stock movement
        stock_entry.purpose = "Material Issue"
        stock_entry.remarks = f"Seeds consumed for Propagation Log: {self.name}"

        # Add the single seed item to the items table
        stock_entry.append("items", {
            "item_code": self.seed_item,
            "qty": self.quantity_seeded,
            "s_warehouse": self.source_warehouse,
            # t_warehouse (target) is not needed for Material Issue
            # uom and valuation rate will be fetched from the Item master
        })

        # Save the new Stock Entry as a draft and then submit it
        stock_entry.insert(ignore_permissions=True)
        stock_entry.submit()

        # Update this Propagation Log with the name of the new Stock Entry
        # We use db_set because the document is already submitted
        self.db_set("generated_stock_entry", stock_entry.name)
        frappe.msgprint(
            f"Stock Entry <a href='/app/stock-entry/{stock_entry.name}' target='_blank'>{stock_entry.name}</a> created successfully.")

    def on_cancel(self):
        """
        This hook runs when the Propagation Log is cancelled.
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
                             "Propagation Log Stock Cancellation Failed")
            frappe.throw(
                f"Failed to cancel Stock Entry {self.generated_stock_entry}: {str(e)}")


@frappe.whitelist()
def get_crop_for_seed_item(item_code):
    """
    Securely fetches the linked 'crop' field for a given seed Item.
    Returns the crop name or None if not found.
    """
    if not item_code:
        return None

    # We use a try-except block to handle cases where the custom field might not exist
    try:
        crop = frappe.db.get_value("Item", item_code, "crop")
        return crop
    except Exception:
        # This can happen if the 'crop' field doesn't exist on the Item doctype
        # or if there's a permission issue not related to the whitelist.
        frappe.log_error(
            f"Failed to fetch 'crop' field for Item {item_code}", "get_crop_for_seed_item")
        return None
