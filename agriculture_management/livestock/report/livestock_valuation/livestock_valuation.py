# Copyright (c) 2025, aminos and contributors
# For license information, please see license.txt

# import frappe


import frappe
from frappe import _

def execute(filters=None):
    if not filters: filters = {}

    # Define the columns that will be displayed in the report
    columns = get_columns()
    
    # Get the processed data
    data = get_data(filters)

    return columns, data

def get_columns():
    """Defines the report's columns and their properties."""
    return [
        {"label": _("Livestock ID"), "fieldname": "livestock_id", "fieldtype": "Link", "options": "Livestock", "width": 160},
        {"label": _("Animal Name"), "fieldname": "animal_name", "fieldtype": "Data", "width": 140},
        {"label": _("Age"), "fieldname": "age", "fieldtype": "Float", "width": 80},
        {"label": _("Acquisition Cost"), "fieldname": "acquisition_cost", "fieldtype": "Currency", "width": 140},
        {"label": _("Calculated Value"), "fieldname": "calculated_value", "fieldtype": "Currency", "width": 140},
        {"label": _("Variance"), "fieldname": "variance", "fieldtype": "Currency", "width": 120},
    ]

def get_data(filters):
    """Fetches and processes the data based on the provided filters."""
    valuation_method = filters.get("valuation_method")
    as_on_date = filters.get("as_on_date")
    
    # Get the list of animals to process
    animals_to_process = get_animals(filters)
    if not animals_to_process:
        return []

    report_data = []
    for animal in animals_to_process:
        acquisition_cost = frappe.db.get_value("Asset", animal.asset, "value_after_depreciation") if animal.asset else 0
        
        calculated_value = 0
        if valuation_method == "Acquisition Cost":
            calculated_value = acquisition_cost
        elif valuation_method == "Standard Cost":
            calculated_value = get_value_by_standard_cost(animal.item_code)
        elif valuation_method == "Last Purchase Price":
            calculated_value = get_value_by_last_purchase_price(animal.item_code, as_on_date)

        variance = calculated_value - acquisition_cost

        report_data.append({
            "livestock_id": animal.name,
            "animal_name": animal.animal_name,
            "age": animal.age,
            "acquisition_cost": acquisition_cost,
            "calculated_value": calculated_value,
            "variance": variance,
        })
        
    return report_data

# --- Helper Functions ---

def get_animals(filters):
    """Returns a list of active Livestock documents to process based on filters."""
    filter_conditions = {"status": "Active"}
    if filters.get("livestock_group"):
        filter_conditions["livestock_group"] = filters.get("livestock_group")

    return frappe.get_all("Livestock",
        filters=filter_conditions,
        fields=["name", "animal_name", "age", "asset", "item_code"]
    )

def get_value_by_standard_cost(item_code):
    """Fetches the standard selling rate from the Item master."""
    if not item_code: return 0
    # You can choose 'standard_buying_rate' if that's more appropriate
    return frappe.db.get_value("Item", item_code, "standard_selling_rate") or 0

def get_value_by_last_purchase_price(item_code, as_on_date):
    """Finds the rate from the last Purchase Invoice for this item type."""
    if not item_code: return 0
    
    last_purchase = frappe.get_all("Purchase Invoice Item",
        filters={
            "item_code": item_code,
            "docstatus": 1,
            "parenttype": "Purchase Invoice",
            "posting_date": ("<=", as_on_date)
        },
        fields=["rate"],
        order_by="posting_date desc",
        limit=1
    )
    
    return last_purchase[0].rate if last_purchase else 0