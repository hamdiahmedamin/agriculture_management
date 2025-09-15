# Copyright (c) 2025, aminos and contributors
# For license information, please see license.txt

import frappe


def execute(filters=None):
    """
    This script provides data specifically for the Water Quality dashboard chart.
    It safely handles empty filters to prevent errors on initial load.
    """
    columns = get_columns()
    data = get_data(filters)
    return columns, data


def get_columns():
    """Defines the columns. These must match the 'X Field' and 'Y Axis' fields in the Dashboard Chart."""
    return [
        {"label": "Timestamp", "fieldname": "Timestamp", "fieldtype": "Datetime"},
        {"label": "Hydroponic System",
            "fieldname": "hydroponic_system", "fieldtype": "Data"},
        {"label": "pH", "fieldname": "pH", "fieldtype": "Float"},
        {"label": "EC", "fieldname": "EC", "fieldtype": "Float"},
        {"label": "Temp C°", "fieldname": "Temp", "fieldtype": "Float"},
    ]
