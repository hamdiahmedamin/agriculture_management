import frappe
from frappe import _

@frappe.whitelist()
def create_qis_for_harvest_items(harvest_log_name, items_to_inspect):
    """
    Creates multiple Quality Inspection documents for a specific Harvest Log.
    This is a standard API function and does not use 'self'.
    """
    # Load the document using the name passed from the client
    doc = frappe.get_doc("Harvest Log", harvest_log_name)

    if isinstance(items_to_inspect, str):
        items_to_inspect = frappe.parse_json(items_to_inspect)

    created_qi_list = []
    for item_data in items_to_inspect:
        item_code = item_data.get("item_code")
        
        # This logic is correct
        if frappe.db.exists("Quality Inspection", {
            "reference_type": "Harvest Log",
            "reference_name": doc.name,
            "item_code": item_code
        }):
            continue

        try:
            qi = frappe.get_doc({
                "doctype": "Quality Inspection",
                "inspection_type": "Incoming",
                "reference_type": "Harvest Log",
                "reference_name": doc.name,
                "item_code": item_code,
                "sample_size": item_data.get("quantity", 1),
                "inspected_by": item_data.get("harvested_by") or frappe.session.user
            })
            qi.insert(ignore_permissions=True)
            created_qi_list.append(qi.name)

            # Link the QI back to the child table row
            for row in doc.harvested_items:
                if row.item_code == item_code and row.name == item_data.get("name"):
                    row.db_set("quality_inspection", qi.name)
        except Exception as e:
            frappe.log_error(f"Failed to create QI for item {item_code} in Harvest Log {doc.name}: {e}")

    if not created_qi_list and items_to_inspect:
        frappe.msgprint(_("No new Quality Inspections were created. They may already exist."))
    
    return created_qi_list