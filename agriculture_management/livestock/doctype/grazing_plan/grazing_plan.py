# Copyright (c) 2025, aminos and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.utils import getdate, date_diff

class GrazingPlan(Document):
    def before_save(self):
        """
        Calculates the rest days for each pasture in the rotation list
        before the document is saved.
        """
        for rotation_row in self.pasture_rotation:
            # Only calculate if we have the necessary data
            if not (rotation_row.pasture and rotation_row.planned_move_in_date):
                rotation_row.rest_days_calculated = 0
                continue

            # Find the most recent 'actual_move_out_date' for this pasture from any
            # OTHER completed rotation in the system.
            last_move_out_date = frappe.db.get_value(
                "Pasture Rotation",  # Child DocType name
                filters={
                    "pasture": rotation_row.pasture,
                    "actual_move_out_date": ("is", "set"), # Ensure the date is not null
                    "parent": ("!=", self.name), # Exclude the current document
                    # Ensure we only look at dates before the planned move-in
                    "actual_move_out_date": ("<", rotation_row.planned_move_in_date) 
                },
                fieldname="actual_move_out_date",
                order_by="actual_move_out_date desc" # Sort to get the latest date first
            )

            if last_move_out_date:
                # Calculate the difference in days
                rest_days = date_diff(getdate(rotation_row.planned_move_in_date), getdate(last_move_out_date))
                rotation_row.rest_days_calculated = rest_days
            else:
                # If no previous record found, this is its first use in the system
                rotation_row.rest_days_calculated = 0