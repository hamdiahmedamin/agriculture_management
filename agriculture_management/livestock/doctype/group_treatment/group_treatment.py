# Copyright (c) 2025, aminos and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.utils import add_days, getdate, flt
from frappe import _


class GroupTreatment(Document):
    def before_save(self):
        """Calculate the withdrawal end date for THIS specific treatment."""
        if self.date:
            longest_period = max(flt(self.milk_withdrawal_period), flt(
                self.meat_withdrawal_period))
            self.withdrawal_end_date = add_days(
                self.date, longest_period) if longest_period > 0 else None

    def before_submit(self):
        """Set the status of THIS treatment record."""
        if self.withdrawal_end_date and getdate(self.withdrawal_end_date) > getdate():
            self.status = "Withdrawal Period Active"
        else:
            self.status = "Completed"

    def on_submit(self):
        """On submit, create the stock entry and update the parent's withdrawal status."""
        self.create_stock_consumption_entry()
        self.update_parent_withdrawal_status()

    def on_cancel(self):
        """On cancel, cancel the stock entry and update the parent's withdrawal status."""
        if self.generated_stock_entry:
            try:
                se = frappe.get_doc("Stock Entry", self.generated_stock_entry)
                if se.docstatus == 1:
                    se.cancel()
                    frappe.msgprint(
                        f"Linked Stock Entry {se.name} has been cancelled.", indicator="orange")
            except frappe.DoesNotExistError:
                pass
        self.update_parent_withdrawal_status()

    def update_parent_withdrawal_status(self):
        """
        Finds the parent (Flock or Animal) and updates its withdrawal status
        based on the latest active treatment OR vaccination.
        """
        group = frappe.get_doc("Livestock Group", self.livestock_group)

        # Find the latest withdrawal date from ALL submitted treatments AND vaccinations for this group.
        all_dates = frappe.db.sql("""
            (SELECT MAX(withdrawal_end_date) FROM `tabGroup Treatment` WHERE livestock_group = %(group)s AND docstatus = 1)
            UNION ALL
            (SELECT MAX(withdrawal_end_date) FROM `tabGroup Vaccination` WHERE livestock_group = %(group)s AND docstatus = 1)
        """, {"group": self.livestock_group})

        valid_dates = [d[0] for d in all_dates if d and d[0]]
        new_date = max(valid_dates) if valid_dates else None

        if group.is_flock:
            flock_name = frappe.db.get_value(
                "Poultry Flock", {"livestock_group": self.livestock_group})
            if flock_name:
                flock = frappe.get_doc("Poultry Flock", flock_name)
                # --- THIS IS THE CRITICAL FIX FOR FLOCK STATUS ---
                if new_date and getdate(new_date) >= getdate():
                    flock.db_set("in_withdrawal_until", new_date)
                    flock.db_set("status", "In Withdrawal")
                else:
                    flock.db_set("in_withdrawal_until", None)
                    flock.db_set("status", "Active")
        else:
            animal_names = [row.animal for row in self.animals if row.animal]
            if animal_names:
                if new_date and getdate(new_date) >= getdate():
                    frappe.db.set_value(
                        "Animal", {"name": ["in", animal_names]}, "in_withdrawal_until", new_date)
                    frappe.db.set_value(
                        "Animal", {"name": ["in", animal_names]}, "status", "In Withdrawal")
                else:
                    frappe.db.set_value(
                        "Animal", {"name": ["in", animal_names]}, "in_withdrawal_until", None)
                    frappe.db.set_value(
                        "Animal", {"name": ["in", animal_names]}, "status", "Active")

    def create_stock_consumption_entry(self):
        if not self.medications_administered:
            return
        group_data = frappe.get_doc(
            "Livestock Group", self.livestock_group).as_dict()
        source_warehouse = group_data.get("group_location")
        if not source_warehouse:
            frappe.throw(
                f"Please set a 'Group Location' on Livestock Group '{self.livestock_group}'.")
        se = frappe.get_doc({"doctype": "Stock Entry", "purpose": "Material Issue", "set_posting_time": 1,
                            "posting_date": self.date, "custom_livestock_group": self.livestock_group})
        for med in self.medications_administered:
            if med.item and flt(med.quantity_used) > 0:
                se.append("items", {"item_code": med.item, "qty": med.quantity_used,
                          "s_warehouse": source_warehouse, "cost_center": group_data.get("cost_center")})
        if not se.items:
            return
        se.insert(ignore_permissions=True)
        se.submit()
        self.db_set("generated_stock_entry", se.name)
        frappe.msgprint(
            f"Stock consumed via <a href='/app/stock-entry/{se.name}'>{se.name}</a>.", indicator="green")
