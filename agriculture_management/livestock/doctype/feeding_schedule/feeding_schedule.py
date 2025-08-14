# Copyright (c) 2025, aminos and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document

class FeedingSchedule(Document):
    def on_submit(self):
        """
        Triggered upon submitting a completed Feeding Schedule.
        Creates a Material Issue Stock Entry for the consumed feed.
        """
        if self.status != "Completed":
            # Only run the logic if the schedule is marked as completed
            return

        # Fetch settings and linked documents
        settings = frappe.get_doc("Livestock Settings")
        group = frappe.get_doc("Livestock Group", self.livestock_group)
        formulation = frappe.get_doc("Feed Formulation", self.feed_formulation)

        if not settings.default_feed_warehouse:
            frappe.throw("Please set the 'Default Feed Warehouse' in Livestock Settings.")
        if not group.cost_center:
            frappe.throw(f"Please set a Cost Center for Livestock Group {group.name}.")

        try:
            se = frappe.new_doc("Stock Entry")
            se.stock_entry_type = "Material Issue"
            se.set_posting_date = True
            se.purpose = "Material Issue"
            
            # This is the key for financial tracking
            se.cost_center = group.cost_center

            # Loop through ingredients in the feed recipe
            for ingredient in formulation.ingredients:
                # Assuming 'percentage' field in Feed Formulation Ingredients child table
                qty_to_issue = (self.quantity_to_feed * (ingredient.percentage or 0)) / 100

                if qty_to_issue > 0:
                    se.append("items", {
                        "item_code": ingredient.item,
                        "qty": qty_to_issue,
                        "s_warehouse": settings.default_feed_warehouse,
                        "cost_center": group.cost_center,
                        "uom": ingredient.uom or frappe.db.get_value("Item", ingredient.item, "stock_uom")
                    })
            
            if not se.items:
                frappe.msgprint("No ingredients to issue based on the formulation percentages.")
                return

            se.insert(ignore_permissions=True) # Ignore perms to allow submission from another doc
            se.submit()

            self.db_set("stock_entry", se.name) # Link the created SE for reference
            frappe.msgprint(f"Stock Entry <a href='/app/stock-entry/{se.name}'>{se.name}</a> created.", indicator="green")

        except Exception as e:
            frappe.log_error(frappe.get_traceback(), "Feeding Schedule Automation Error")
            frappe.throw(str(e))