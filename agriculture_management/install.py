import click
import agriculture_management.datadb as datadb
import frappe
from frappe import _
from frappe.desk.page.setup_wizard.setup_wizard import add_all_roles_to


def after_install():
    click.echo("Installing Agriculture Customizations ...")
    add_item_group()
    # add_crop_category()
    add_agriculture_analysis_criteria()
    add_custom_fields_to_time_log()
    add_custom_fields_for_quality_inspection()


def after_sync():
	create_agriculture_roles()
	add_crop_category()
	add_pest_categories()
	# set_default_certificate_print_format()
	add_all_roles_to("Administrator")

def add_item_group():
    for itemgroup in datadb.itemgroups:
        if not frappe.db.exists("Item Group", itemgroup.get("item_group_name")):
            frappe.get_doc(
				{
					"doctype": "Item Group",
					"item_group_name": itemgroup.get(_("item_group_name")),
					"is_group": itemgroup.get("is_group"),
					"parent_item_group": itemgroup.get("parent_item_group"),
				}
			).save()
        """ if not frappe.get_value("Item Group", itemgroup.get("item_group_name")):
            item_group = frappe.new_doc("Item Group")
            item_group.item_group_name = itemgroup.get("item_group_name")
            item_group.parent_item_group = _("All Item Groups")
            item_group.save() """
    click.echo("Agriculture Items Group added ...")

def add_crop_category():
    for cropcategory in datadb.cropcategories:
        """ if not frappe.db.exists("Crop Category",cropcategory.get("category_name")):
            frappe.get_doc(
				{
					"doctype": "Crop Category",	
    				"category_name": _(cropcategory.get("category_name")),
					"category_description": _(cropcategory.get("category_description")),      
				}
			).save() """
        if not frappe.get_value("Crop Category", cropcategory.get("category_name")):
            category = frappe.new_doc("Crop Category")
            category.name = cropcategory.get(_("category_name"))
            category.category_name = cropcategory.get(_("category_name"))
            category.category_description = cropcategory.get(_("category_description"))
            category.save()
            
def add_pest_categories():
    frappe.get_doc(
				{
					"doctype": "Pest Categories",
					"pest_category_name":"Pest Categories Group",
					"is_group": 1,
					"is_main": 1,
					"parent_pest_categories":"",
				}
			).save()
    for pestcategory in datadb.pestcategories:
        if not frappe.get_value("Pest Categories", pestcategory.get("pest_category_name")):
            category = frappe.new_doc("Pest Categories")
            category.name = pestcategory.get(_("pest_category_name"))
            category.is_group = pestcategory.get("is_group")
            category.pest_category_name = pestcategory.get(_("pest_category_name"))
            category.parent_pest_categories = pestcategory.get(_("parent_pest_categories"))
            category.save()
            
def add_agriculture_analysis_criteria():    
    for analysiscriteria in datadb.analysiscriterias:
        if not frappe.db.exists("Agriculture Analysis Criteria", analysiscriteria.get("title")):
            frappe.get_doc(
				{
					"doctype": "Agriculture Analysis Criteria",
					"title": analysiscriteria.get("title"),
					"standard": analysiscriteria.get("standard"),
					"linked_doctype": analysiscriteria.get("linked_doctype"),
				}
			).save()
    click.echo("Agriculture Analysis Criteria added ...")
            
def create_agriculture_roles():
	create_agriculture_user_role()
	create_agriculture_manager_role()
	click.echo("Agriculture Roles created ...")

def create_agriculture_user_role():
	if not frappe.db.exists("Role", "Agriculture User"):
		role = frappe.get_doc(
			{
				"doctype": "Role",
				"role_name": "Agriculture User",
				"home_page": "",
				"desk_access": 0,
			}
		)
		role.save()
def create_agriculture_manager_role():
	if not frappe.db.exists("Role", "Agriculture Manager"):
		role = frappe.get_doc(
			{
				"doctype": "Role",
				"role_name": "Agriculture Manager",
				"home_page": "",
				"desk_access": 0,
			}
		)
		role.save()

def add_custom_fields_to_time_log():
	"""
	This function adds custom link fields to the 'Timesheet Detail' DocType
	to connect it to our custom hydroponics workflow.
	"""
	# --- Field 1: Link to Hydroponic Crop Cycle ---
	if not frappe.db.exists("Custom Field", {"dt": "Timesheet Detail", "fieldname": "custom_linked_crop_cycle"}):
		print("Creating custom field 'custom_linked_crop_cycle' in Timesheet Detail...")
		
		# Create a new 'Custom Field' document
		custom_field = frappe.new_doc("Custom Field")
		custom_field.dt = "Timesheet Detail"  # The DocType we are modifying
		custom_field.fieldname = "custom_linked_crop_cycle"
		custom_field.label = "Linked Hydroponic Crop Cycle"
		custom_field.fieldtype = "Link"
		custom_field.options = "Hydroponic Crop Cycle"  # The DocType to link to
		
		# This determines where the new field appears on the form.
		# We'll place it after the 'activity_type' field.
		custom_field.insert_after = "activity_type"
		
		# Save the new Custom Field document
		custom_field.insert()
		print("...done.")
	else:
		print("'custom_linked_crop_cycle' field already exists in Timesheet Detail.")

	# --- Field 2: Link to Sanitization Log ---
	if not frappe.db.exists("Custom Field", {"dt": "Timesheet Detail", "fieldname": "custom_linked_sanitization_log"}):
		print("Creating custom field 'custom_linked_sanitization_log' in Timesheet Detail...")
		
		custom_field = frappe.new_doc("Custom Field")
		custom_field.dt = "Timesheet Detail"
		custom_field.fieldname = "custom_linked_sanitization_log"
		custom_field.label = "Linked Sanitization Log"
		custom_field.fieldtype = "Link"
		custom_field.options = "Sanitization Log"
		
		# Place this field right after the one we just created
		custom_field.insert_after = "custom_linked_crop_cycle"
		
		custom_field.insert()
		print("...done.")
	else:
		print("'custom_linked_sanitization_log' field already exists in Timesheet Detail.")
	
	frappe.db.commit()
      
def add_custom_fields_for_quality_inspection():
    # Add a field to Harvest Log to link it back to the Quality Inspection
    if not frappe.db.exists("Custom Field", {"dt": "Harvest Log", "fieldname": "custom_linked_quality_inspection"}):
        click.echo("Creating custom field 'custom_linked_quality_inspection' in Harvest Log...")
        custom_field = frappe.new_doc("Custom Field")
        custom_field.dt = "Harvest Log"
        custom_field.fieldname = "custom_linked_quality_inspection"
        custom_field.label = "Linked Quality Inspection"
        custom_field.fieldtype = "Link"
        custom_field.options = "Quality Inspection"
        custom_field.read_only = 1 # This field will be set by our script
        custom_field.insert_after = "status"
        custom_field.insert()