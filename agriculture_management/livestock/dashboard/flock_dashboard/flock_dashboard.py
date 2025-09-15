import frappe
from frappe.utils import flt


@frappe.whitelist()
def get_data(flock_name):
    """
    Fetches the precise, real-time stock data for a specific Poultry Flock.
    """
    if not flock_name:
        return {}

    flock_doc = frappe.get_doc("Poultry Flock", flock_name)
    if not flock_doc.batch or not flock_doc.coop:
        return {}

    # Get the definitive quantity from the Stock Ledger for the specific batch and coop.
    ledger_data = frappe.db.sql("""
        SELECT SUM(actual_qty)
        FROM `tabStock Ledger Entry`
        WHERE batch_no = %s AND warehouse = %s
    """, (flock_doc.batch, flock_doc.coop))

    actual_qty = flt(ledger_data[0][0]
                     ) if ledger_data and ledger_data[0][0] else 0

    return {
        "warehouse": flock_doc.coop,
        "actual_qty": actual_qty,
        "stock_uom": frappe.get_cached_value("Item", flock_doc.item, "stock_uom")
    }
