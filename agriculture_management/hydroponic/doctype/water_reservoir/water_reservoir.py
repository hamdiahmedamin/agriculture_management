# Copyright (c) 2023, aminos and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class WaterReservoir(Document):
    pass


@frappe.whitelist()
def get_latest_reading_for_reservoir(reservoir_name):
    """
    Finds the most recent 'Water Quality Reading' for a specific reservoir.
    """
    try:
        latest_reading = frappe.get_all(
            "Water Quality Reading",
            filters={"water_reservoir": reservoir_name, "docstatus": 1},
            fields=["ph", "electrical_conductivity",
                    "water_temperature", "modified"],
            order_by="modified desc",
            limit=1
        )
        return latest_reading[0] if latest_reading else None
    except Exception as e:
        frappe.log_error(
            f"Error fetching reading for reservoir {reservoir_name}: {e}")
        return None
