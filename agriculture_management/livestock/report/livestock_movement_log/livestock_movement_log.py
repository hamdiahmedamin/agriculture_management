# Copyright (c) 2025, aminos and contributors
# For license information, please see license.txt

import frappe


def execute(filters=None):
    columns = get_columns()
    data = get_data(filters)
    return columns, data


def get_columns():
    """Defines the columns that will be displayed in the report."""
    return [
        {"label": "Movement Date", "fieldname": "movement_date",
            "fieldtype": "Date", "width": 130},
        {"label": "Movement Type", "fieldname": "movement_type",
            "fieldtype": "Data", "width": 120},
        {"label": "Animal", "fieldname": "animal",
            "fieldtype": "Link", "options": "Animal", "width": 150},
        {"label": "Livestock Group", "fieldname": "livestock_group",
            "fieldtype": "Link", "options": "Livestock Group", "width": 150},
        {"label": "From Location", "fieldname": "from_location",
            "fieldtype": "Link", "options": "Warehouse", "width": 150},
        {"label": "To Location", "fieldname": "to_location",
            "fieldtype": "Link", "options": "Warehouse", "width": 150},
        {"label": "Reason", "fieldname": "reason",
            "fieldtype": "Data", "width": 150},
        {"label": "Movement Record", "fieldname": "name", "fieldtype": "Link",
            "options": "Livestock Movement", "width": 180},
    ]


def get_data(filters):
    """Fetches and filters the movement history data."""
    conditions = []
    values = {}

    # Build conditions based on the user's filters
    if filters.get("movement_date"):
        conditions.append(
            "movement_date BETWEEN %(from_date)s AND %(to_date)s")
        values["from_date"] = filters["movement_date"][0]
        values["to_date"] = filters["movement_date"][1]

    if filters.get("animal"):
        conditions.append("animal = %(animal)s")
        values["animal"] = filters["animal"]

    if filters.get("livestock_group"):
        conditions.append("livestock_group = %(livestock_group)s")
        values["livestock_group"] = filters["livestock_group"]

    if filters.get("from_location"):
        conditions.append("from_location = %(from_location)s")
        values["from_location"] = filters["from_location"]

    if filters.get("to_location"):
        conditions.append("to_location = %(to_location)s")
        values["to_location"] = filters["to_location"]

    if filters.get("reason"):
        conditions.append("reason = %(reason)s")
        values["reason"] = filters["reason"]

    # Always exclude cancelled documents
    # Only show submitted (finalized) movements
    conditions.append("docstatus = 1")

    where_clause = " AND ".join(conditions)

    # The main SQL query targets the 'tabLivestock Movement' table.
    query = f"""
        SELECT
            name,
            movement_date,
            movement_type,
            animal,
            livestock_group,
            from_location,
            to_location,
            reason
        FROM
            `tabLivestock Movement`
        WHERE
            {where_clause}
        ORDER BY
            movement_date DESC
    """

    result = frappe.db.sql(query, values, as_dict=1)
    return result
