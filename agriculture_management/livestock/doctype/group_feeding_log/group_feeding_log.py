# Copyright (c) 2025, aminos and contributors
# For license information, please see license.txt

# group_feeding_log.py
import frappe
from frappe.model.document import Document


class GroupFeedingLog(Document):
    def on_submit(self):
        """
        On submission, create and submit a 'Material Issue' Stock Entry
        to consume the feed items from inventory.
        """
        # Get the source warehouse from the Livestock Group's location
        source_warehouse = frappe.db.get_value(
            "Livestock Group", self.livestock_group, "group_location")
        if not source_warehouse:
            frappe.throw(
                f"Please set a 'Group Location' for the Livestock Group {self.livestock_group}")

        # Create the Stock Entry
        se = frappe.get_doc({
            "doctype": "Stock Entry",
            "stock_entry_type": "Material Issue",
            "set_posting_time": 1,
            "posting_date": self.date,
            "cost_center": self.cost_center,
            "custom_gfl_ref": self.name  # Custom Link field on Stock Entry
        })

        # Copy the items from the feeding log to the stock entry
        for item in self.items:
            se.append("items", {
                "item_code": item.item_code,
                "qty": item.qty,
                "s_warehouse": source_warehouse,
                "cost_center": self.cost_center,
                "uom": item.uom,
                "basic_rate": item.basic_rate,
                "basic_amount": item.basic_amount
            })

        se.insert(ignore_permissions=True)
        se.submit()

        frappe.msgprint(
            f"Stock Entry {se.name} created to record feed consumption.")
