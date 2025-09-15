# Copyright (c) 2025, aminos and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe import _


class LivestockPerformanceLog(Document):
    def on_submit(self):
        """
        On submit, create stock entries for new inventory and trigger an
        update on the parent Poultry Flock document.
        """
        inventory_log_types = ["Egg Collection", "Wool Shear", "Milk Yield"]
        if self.log_type in inventory_log_types:
            self.create_stock_entry_for_production()

        # --- THIS IS THE CRITICAL FIX ---
        # After any log is submitted, find the parent flock and tell it to update itself.
        # This ensures that weight logs and egg logs are immediately reflected on the flock.
        if self.log_for == "Poultry Flock" and self.poultry_flock:
            try:
                flock = frappe.get_doc("Poultry Flock", self.poultry_flock)
                flock.update_performance_metrics()
                flock.save(ignore_permissions=True)
            except frappe.DoesNotExistError:
                frappe.log_error(
                    f"Could not find Poultry Flock {self.poultry_flock} to update metrics.")
        # --- END OF FIX ---

    def on_cancel(self):
        """If the log is cancelled, also cancel the linked Stock Entry."""
        if self.generated_stock_entry:
            try:
                se = frappe.get_doc("Stock Entry", self.generated_stock_entry)
                if se.docstatus == 1:
                    se.cancel()
                    frappe.msgprint(
                        f"Linked Stock Entry {se.name} has been cancelled.", indicator="orange")
            except Exception as e:
                frappe.log_error(frappe.get_traceback())

    def create_stock_entry_for_production(self):
        if not self.item:
            frappe.throw(
                f"Please select the 'Produced Item' for the log type '{self.log_type}'.")

        target_warehouse = self.get_target_warehouse()
        if not target_warehouse:
            frappe.throw(
                f"Could not determine the target warehouse for the log.")

        batch_no = None
        # --- THIS IS THE DEFINITIVE BATCH CREATION LOGIC ---
        if self.log_type == "Egg Collection":
            # 1. Create a new, unique Batch for this egg collection.
            batch = frappe.get_doc({
                "doctype": "Batch",
                "item": self.item,
                # Naming the batch after the log creates a perfect traceability link.
                "batch_id": f"{self.name}-EGGS"
            }).insert(ignore_permissions=True)
            batch_no = batch.name
            frappe.msgprint(
                _("Created new Batch <b>{0}</b> for this egg collection.").format(batch_no))
        # --- END OF NEW LOGIC ---

        # 2. Create the Stock Entry using the new batch.
        se = self.create_stock_receipt(target_warehouse, batch_no)
        self.db_set("generated_stock_entry", se.name)
        frappe.msgprint(
            f"Stock Entry <a href='/app/stock-entry/{se.name}'>{se.name}</a> created.", indicator="green")

    def get_target_warehouse(self):
        """Helper function to find the correct warehouse."""
        if self.log_for == "Poultry Flock" and self.poultry_flock:
            return frappe.db.get_value("Poultry Flock", self.poultry_flock, "coop")
        elif self.log_for == "Individual Animal" and self.animal:
            return frappe.db.get_value("Animal", self.animal, "location_pen")
        return frappe.db.get_value("Livestock Settings", None, "default_product_warehouse")

    def create_stock_receipt(self, target_warehouse, batch_no=None):
        """Creates and submits a Material Receipt Stock Entry."""
        item_line = {
            "item_code": self.item,
            "qty": self.quantity,
            "uom": self.uom,
            "use_serial_batch_fields": 1,
            "t_warehouse": target_warehouse
        }
        if batch_no:
            item_line["batch_no"] = batch_no

        se = frappe.get_doc({
            "doctype": "Stock Entry",
            "stock_entry_type": "Material Receipt",
            "purpose": "Material Receipt",
            "set_posting_time": 1, "posting_date": self.date,
            "items": [item_line]
        })
        se.insert(ignore_permissions=True)
        se.submit()
        return se
