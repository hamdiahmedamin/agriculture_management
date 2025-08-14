import agriculture_management.datadb as datadb
import frappe


def before_uninstall():
	delete_agriculture_item_group()
	delete_agriculture_crop_category()
	delete_agriculture_roles()
	delete_custom_fields_from_time_log()
	delete_custom_fields_for_quality_inspection()

def delete_agriculture_item_group():
	for itemgroup in datadb.itemgroups:
		if frappe.db.exists("Item Group", itemgroup.get("item_group_name")):
			frappe.db.delete("Item Group", itemgroup)

def delete_agriculture_crop_category():
    for cropcategory in datadb.cropcategories:
        if frappe.db.exists("Crop Category", cropcategory.get("category_name")):
            frappe.db.delete("Crop Category", cropcategory)

def delete_agriculture_roles():
	roles = ["Agriculture User", "Agriculture Manager"]
	for role in roles:
		if frappe.db.exists("Role", role):
			frappe.db.delete("Role", role)

def delete_custom_fields_from_time_log(): # You can optionally rename this function
	"""
	This function removes the custom link fields from the 'Timesheet Detail' DocType
	that were added by this app.
	"""
	# --- Field 1: Link to Hydroponic Crop Cycle ---
	field_name_1 = "custom_linked_crop_cycle"
	if frappe.db.exists("Custom Field", {"dt": "Timesheet Detail", "fieldname": field_name_1}):
		# The unique name is "ParentDocType-fieldname"
		custom_field_name_1 = f"Timesheet Detail-{field_name_1}" # <-- CORRECTED
		frappe.delete_doc("Custom Field", custom_field_name_1, ignore_permissions=True, force=True)
		print(f"Deleted custom field '{field_name_1}' from Timesheet Detail.")

	# --- Field 2: Link to Sanitization Log ---
	field_name_2 = "custom_linked_sanitization_log"
	if frappe.db.exists("Custom Field", {"dt": "Timesheet Detail", "fieldname": field_name_2}):
		custom_field_name_2 = f"Timesheet Detail-{field_name_2}" # <-- CORRECTED
		frappe.delete_doc("Custom Field", custom_field_name_2, ignore_permissions=True, force=True)
		print(f"Deleted custom field '{field_name_2}' from Timesheet Detail.")

	frappe.db.commit()

def delete_custom_fields_for_quality_inspection():
    """	Removes the custom fields for Quality Inspection integration."""
    if frappe.db.exists("Custom Field", {"dt": "Harvest Log", "fieldname": "custom_linked_quality_inspection"}):
        frappe.delete_doc("Custom Field", "Harvest Log-custom_linked_quality_inspection", ignore_permissions=True, force=True)