# Copyright (c) 2025, aminos and contributors
# For license information, please see license.txt

import frappe
from collections import defaultdict


def execute(filters=None):
    columns = get_columns()
    data = get_data(filters)
    return columns, data


def get_columns():
    return [
        {"label": "Crop Cycle", "fieldname": "crop_cycle",
            "fieldtype": "Link", "options": "Crop Cycle", "width": 140},
        {"label": "Crop", "fieldname": "crop",
            "fieldtype": "Link", "options": "Crop", "width": 120},
        {"label": "Growth Method", "fieldname": "growth_method",
            "fieldtype": "Data", "width": 120},
        {"label": "Harvest Date", "fieldname": "harvest_date",
            "fieldtype": "Date", "width": 110},
        {"label": "Harvested Weight (kg)", "fieldname": "harvested_weight",
         "fieldtype": "Float", "width": 120},
        {"label": "Sale Price/kg", "fieldname": "sale_price",
            "fieldtype": "Currency", "width": 110},
        {"label": "Total Revenue", "fieldname": "total_revenue",
            "fieldtype": "Currency", "width": 120},
        # --- MODIFIED COLUMN LABELS FOR ACCURACY ---
        {"label": "Total Operational Cost", "fieldname": "total_cost",
            "fieldtype": "Currency", "width": 140},
        {"label": "Net Profit", "fieldname": "net_profit",  # Renamed from gross_profit
            "fieldtype": "Currency", "width": 120},
        {"label": "Profit Margin (%)", "fieldname": "profit_margin",
         "fieldtype": "Float", "width": 110},
        {"label": "Profit per kg", "fieldname": "profit_per_kg",
            "fieldtype": "Currency", "width": 110},
    ]


def get_data(filters):
    """Fetches and processes data from multiple sources to calculate profitability."""

    # --- 1. Get Base Data from Crop Cycle and its linked Harvests (Unchanged) ---
    conditions = []
    if filters.get("date_range"):
        start_date, end_date = filters["date_range"]
        conditions.append(
            f"summary.harvest_date BETWEEN '{start_date}' AND '{end_date}'")
    if filters.get("crop_cycle"):
        conditions.append(f"cc.name = '{filters['crop_cycle']}'")
    if filters.get("growth_method"):
        conditions.append(f"cc.growth_method = '{filters['growth_method']}'")
    where_clause = " AND ".join(conditions) if conditions else "1=1"

    harvests = frappe.db.sql(f"""
        SELECT cc.name AS crop_cycle, cc.crop, cc.growth_method, summary.harvest_date,
            hl.total_weight_gross AS harvested_weight, hli.item_code
        FROM `tabCrop Cycle Harvest Summary` AS summary
        JOIN `tabCrop Cycle` AS cc ON summary.parent = cc.name
        JOIN `tabHarvest Log` as hl ON summary.harvest_log = hl.name
        JOIN `tabHarvest Log Item` as hli ON hli.parent = hl.name
        WHERE cc.docstatus = 1 AND {where_clause}
    """, as_dict=True)

    if not harvests:
        return []
    crop_cycles = list(set([h.crop_cycle for h in harvests]))

    # --- 2. Calculate Total Costs ---
    costs = defaultdict(float)
    # Dosing Costs (Unchanged)
    dosing_costs = frappe.db.sql(
        """...""", {"crop_cycles": crop_cycles}, as_dict=True)
    for row in dosing_costs:
        costs[row.crop_cycle] += row.cost or 0
    # Sanitization Costs (Unchanged)
    systems_used = frappe.get_all("Crop Cycle", ...)
    if systems_used:
        sanitization_costs = frappe.db.sql(
            """...""", {"systems": systems_used}, as_dict=True)
        # ... (cost attribution logic is unchanged)

    # --- NEW: Costs from the Expense Log ---
    expense_log_costs = frappe.db.sql("""
        SELECT
            crop_cycle,
            SUM(amount) as total_expense
        FROM
            `tabExpense Log`
        WHERE
            crop_cycle IN %(crop_cycles)s
            AND docstatus = 1
        GROUP BY
            crop_cycle
    """, {"crop_cycles": crop_cycles}, as_dict=True)

    for row in expense_log_costs:
        costs[row.crop_cycle] += row.total_expense or 0
    # --- END OF NEW CODE ---

    # --- 3. Get Item Sale Prices (Unchanged) ---
    item_codes = list(set([h.item_code for h in harvests if h.item_code]))
    item_prices = {}
    if item_codes:
        price_data = frappe.get_all("Item Price", ...)
        for price in price_data:
            if price.item_code not in item_prices:
                item_prices[price.item_code] = price.price_list_rate

    # --- 4. Combine Data and Calculate Profitability ---
    report_data = []
    for h in harvests:
        sale_price = item_prices.get(h.item_code, 0)
        total_revenue = h.harvested_weight * sale_price
        total_cost = costs.get(h.crop_cycle, 0)
        net_profit = total_revenue - total_cost  # Renamed from gross_profit
        profit_margin = (net_profit / total_revenue *
                         100) if total_revenue else 0
        profit_per_kg = (
            net_profit / h.harvested_weight) if h.harvested_weight else 0

        # Append data using the new fieldname 'net_profit'
        report_data.append({
            "crop_cycle": h.crop_cycle, "crop": h.crop, "growth_method": h.growth_method, "harvest_date": h.harvest_date,
            "harvested_weight": h.harvested_weight, "sale_price": sale_price, "total_revenue": total_revenue,
            "total_cost": total_cost, "net_profit": net_profit, "profit_margin": profit_margin, "profit_per_kg": profit_per_kg,
        })

    return report_data
