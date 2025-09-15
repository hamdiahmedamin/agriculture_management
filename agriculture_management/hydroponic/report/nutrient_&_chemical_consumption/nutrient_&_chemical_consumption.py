# Copyright (c) 2025, aminos and contributors
# For license information, please see license.txt

import frappe
from collections import defaultdict


def execute(filters=None):
    """
    Fetches actual consumption data from Dosing Logs and Sanitization Logs,
    aggregates it by Item, and calculates the total cost.
    """
    data = get_data(filters)
    columns = get_columns()
    return columns, data


def get_columns():
    """Defines the columns for the report's data table."""
    return [
        {"label": "Item", "fieldname": "item_code",
            "fieldtype": "Link", "options": "Item", "width": 180},
        {"label": "Item Group", "fieldname": "item_group",
            "fieldtype": "Link", "options": "Item Group", "width": 140},
        {"label": "Category", "fieldname": "category",
            "fieldtype": "Data", "width": 120},
        {"label": "Total Quantity Used", "fieldname": "total_qty",
            "fieldtype": "Float", "width": 150},
        {"label": "UoM", "fieldname": "uom",
            "fieldtype": "Link", "options": "UOM", "width": 80},
        {"label": "Valuation Rate", "fieldname": "valuation_rate",
            "fieldtype": "Currency", "width": 120},
        {"label": "Total Value", "fieldname": "total_value",
            "fieldtype": "Currency", "width": 140}
    ]


def get_data(filters):
    """Fetches and aggregates consumption data from transactional logs."""

    consumption = defaultdict(lambda: {"total_qty": 0, "sources": set()})

    date_conditions = ""
    if filters.get("date_range"):
        start_date, end_date = filters["date_range"]
        # The date field is named differently in each log, so we apply it separately.

    # --- 1. Aggregate Chemicals from Sanitization Logs ---
    sanitization_date_conditions = ""
    if filters.get("date_range"):
        start_date, end_date = filters["date_range"]
        sanitization_date_conditions = f" AND DATE(parent.sanitization_date) BETWEEN '{start_date}' AND '{end_date}'"

    sanitization_data = frappe.db.sql(f"""
        SELECT
            child.sanitizing_agent AS item_code,
            SUM(child.quantity_used) AS total_used
        FROM
            `tabSanitization Chemical` AS child
        JOIN
            `tabSanitization Log` AS parent ON child.parent = parent.name
        WHERE
            parent.docstatus = 1 {sanitization_date_conditions}
        GROUP BY
            child.sanitizing_agent
    """, as_dict=True)

    for row in sanitization_data:
        consumption[row['item_code']]['total_qty'] += row['total_used']
        consumption[row['item_code']]['sources'].add('Chemical')

    # --- 2. Aggregate Nutrients from the new Dosing Log ---
    dosing_date_conditions = ""
    if filters.get("date_range"):
        start_date, end_date = filters["date_range"]
        dosing_date_conditions = f" AND DATE(parent.dosing_date) BETWEEN '{start_date}' AND '{end_date}'"

    dosing_data = frappe.db.sql(f"""
        SELECT
            child.item AS item_code,
            SUM(child.quantity_used) AS total_used
        FROM
            `tabDosing Log Item` AS child
        JOIN
            `tabDosing Log` AS parent ON child.parent = parent.name
        WHERE
            parent.docstatus = 1 {dosing_date_conditions}
        GROUP BY
            child.item
    """, as_dict=True)

    for row in dosing_data:
        consumption[row['item_code']]['total_qty'] += row['total_used']
        consumption[row['item_code']]['sources'].add('Nutrient')

    # --- 3. Fetch Item Details and Finalize Data ---
    if not consumption:
        return []

    item_codes = list(consumption.keys())
    item_details_map = {
        d.name: d for d in frappe.get_all(
            "Item",
            filters={"name": ("in", item_codes)},
            fields=["name", "stock_uom", "item_group", "standard_rate"]
        )
    }

    final_report_data = []
    for item_code, data in consumption.items():
        item_details = item_details_map.get(item_code)
        if not item_details:
            continue

        if filters.get("item_group") and item_details.item_group != filters.get("item_group"):
            continue

        valuation_rate = item_details.standard_rate or 0
        total_value = data['total_qty'] * valuation_rate

        final_report_data.append({
            "item_code": item_code,
            "item_group": item_details.item_group,
            "category": ", ".join(sorted(list(data['sources']))),
            "total_qty": data['total_qty'],
            "uom": item_details.stock_uom,
            "valuation_rate": valuation_rate,
            "total_value": total_value
        })

    return final_report_data
