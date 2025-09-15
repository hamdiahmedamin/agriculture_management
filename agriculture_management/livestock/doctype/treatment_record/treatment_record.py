# Copyright (c) 2025, aminos and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.utils import add_days, getdate, flt
from frappe import _


class TreatmentRecord(Document):
    def before_save(self):
        """Calculate the withdrawal end date for THIS specific treatment before saving."""
        if self.date_of_treatment:
            longest_period = max(flt(self.milk_withdrawal_period), flt(
                self.meat_withdrawal_period))
            if longest_period > 0:
                self.withdrawal_end_date = add_days(
                    self.date_of_treatment, longest_period)
            else:
                self.withdrawal_end_date = None

    def before_submit(self):
        """
        This is the correct hook for all final logic before submission.
        1. Set the status of THIS treatment record.
        2. Update the parent Animal's status and withdrawal date.
        """
        # --- 1. SET THIS DOCUMENT'S STATUS ---
        if self.withdrawal_end_date and getdate(self.withdrawal_end_date) > getdate():
            self.status = "Withdrawal Period Active"
        else:
            self.status = "Completed"

        # --- 2. UPDATE THE PARENT ANIMAL (MOVED FROM on_submit) ---
        if self.animal and self.withdrawal_end_date and getdate(self.withdrawal_end_date) >= getdate():
            animal = frappe.get_doc("Animal", self.animal)
            final_withdrawal_date = getdate(self.withdrawal_end_date)

            # Determine the latest date between the existing and the new period
            if animal.in_withdrawal_until and getdate(animal.in_withdrawal_until) > final_withdrawal_date:
                final_withdrawal_date = getdate(animal.in_withdrawal_until)

            # Use .set() here as it's safe within before_submit on another doc
            animal.set("in_withdrawal_until", final_withdrawal_date)
            animal.set("status", "In Withdrawal")
            # Save the changes to the Animal doc
            animal.save(ignore_permissions=True)

    def on_submit(self):
        """
        The on_submit hook should now be empty or used only for actions that
        do not modify other documents, like logging.
        """
        pass

    def on_cancel(self):
        """Recalculate the withdrawal date and status for the animal."""
        if self.animal:
            latest_date_data = frappe.db.sql("""
                SELECT MAX(withdrawal_end_date)
                FROM `tabTreatment Record`
                WHERE animal = %s AND docstatus = 1 AND name != %s
            """, (self.animal, self.name))

            new_date = latest_date_data[0][0] if latest_date_data and latest_date_data[0][0] else None

            animal = frappe.get_doc("Animal", self.animal)
            if not new_date or getdate(new_date) < getdate():
                animal.status = "Active"
                animal.in_withdrawal_until = None
            else:
                animal.in_withdrawal_until = new_date

            animal.save(ignore_permissions=True)
            frappe.msgprint(
                f"Recalculated withdrawal period and status for Animal '{self.animal}'.")
