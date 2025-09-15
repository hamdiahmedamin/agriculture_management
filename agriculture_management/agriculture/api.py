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
            frappe.log_error(
                f"Failed to create QI for item {item_code} in Harvest Log {doc.name}: {e}")

    if not created_qi_list and items_to_inspect:
        frappe.msgprint(
            _("No new Quality Inspections were created. They may already exist."))

    return created_qi_list


@frappe.whitelist()
def get_log_context(crop_cycle_name):
    """
    Securely fetches context data from a Crop Cycle to pre-fill various logs.
    This version correctly uses the 'hydroponic_system' link field.
    """
    if not crop_cycle_name:
        return None

    # Fetch the core Crop Cycle document
    crop_cycle_doc = frappe.get_doc("Crop Cycle", crop_cycle_name)

    context = {
        "growth_method": crop_cycle_doc.growth_method,
        "company": crop_cycle_doc.company,
        "land_unit": crop_cycle_doc.land_unit,
        "hydroponic_system": crop_cycle_doc.hydroponic_system,
        "growing_zones": [zone.growing_zone for zone in crop_cycle_doc.growing_zones]
    }

    # --- CORRECTED LOOKUP LOGIC ---
    water_source = None
    # Check if the growth method is Hydroponic AND if a system is linked
    if context["growth_method"] == "Hydroponic" and context["hydroponic_system"]:
        try:
            # The 'hydroponic_system' field in Crop Cycle IS the linked Asset.
            asset_name = context["hydroponic_system"]

            # Step 1: From the Asset, get the Water Reservoir
            water_reservoir = frappe.db.get_value(
                "Asset", asset_name, "custom_water_reservoir")

            if water_reservoir:
                # Step 2: From the Water Reservoir, get the Water Source
                water_source = frappe.db.get_value(
                    "Water Reservoir", water_reservoir, "reservoir_water_source")

        except Exception as e:
            frappe.log_error(
                f"Could not complete the multi-level fetch for Water Source. "
                f"Started from Asset {context['hydroponic_system']}. Error: {e}",
                "get_log_context"
            )

    context["water_source"] = water_source
    # --- END OF CORRECTED LOGIC ---

    return context


@frappe.whitelist()
def generate_todos_from_template(template_name, reference_doctype, reference_name):
    """
    Creates multiple ToDo documents based on the steps in a Task Template.
    """
    template = frappe.get_doc("Task Template", template_name)
    count = 0

    for step in template.instructions:
        # Create a new ToDo document for each step in the template
        todo = frappe.new_doc("ToDo")
        todo.description = step.description

        # Link the ToDo back to the source document (e.g., the Sanitization Log)
        todo.reference_type = reference_doctype
        todo.reference_name = reference_name

        # You could also set 'assigned_to' here based on roles or other logic

        todo.insert(ignore_permissions=True)
        count += 1

    return {"count": count}


@frappe.whitelist()
def run_profitability_report(filters=None):
    """
    A whitelisted function that runs the Crop Profitability Report's get_data function.
    """
    if not filters:
        filters = {}

    # IMPORTANT: Make sure this path is correct for your report's location
    report_path = (
        "agriculture_management.agriculture.report.crop_profitability_report.crop_profitability_report.get_data"
    )

    try:
        report_get_data_func = frappe.get_attr(report_path)
    except Exception as e:
        frappe.throw(
            f"Could not find the report script at the path: {report_path}. Error: {e}")

    report_data = report_get_data_func(filters)
    return report_data
