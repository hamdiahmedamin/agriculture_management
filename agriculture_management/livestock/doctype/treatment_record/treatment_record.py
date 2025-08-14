# Copyright (c) 2025, aminos and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.utils import add_days, getdate

class TreatmentRecord(Document):
    def before_save(self):
        """
        Calculates the final withdrawal date based on the longest period specified.
        This runs every time the document is saved.
        """
        if not self.date_of_treatment:
            return

        # Calculate the end dates based on the withdrawal periods
        milk_end_date = add_days(self.date_of_treatment, self.milk_withdrawal_period or 0)
        meat_end_date = add_days(self.date_of_treatment, self.meat_withdrawal_period or 0)

        # The final, official withdrawal date is the latest of the two potential end dates
        self.withdrawal_end_date = max(getdate(milk_end_date), getdate(meat_end_date))

    def before_submit(self):
        """
        Sets the status of the treatment record when it is submitted.
        This transitions the document from a plan to an active event.
        """
        # Check if any withdrawal period is specified.
        # If no withdrawal is needed, the treatment is completed immediately.
        has_withdrawal_period = (self.milk_withdrawal_period or 0) > 0 or \
                                (self.meat_withdrawal_period or 0) > 0

        if has_withdrawal_period:
            # If there is a withdrawal period, the status becomes 'Active'
            self.status = "Withdrawal Period Active"
        else:
            # If no withdrawal is needed (e.g., a simple vitamin shot),
            # the treatment is considered completed upon submission.
            self.status = "Completed"