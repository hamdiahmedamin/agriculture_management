import agriculture_management.datadb as datadb
import frappe
from frappe import _
from frappe.desk.page.setup_wizard.setup_wizard import add_all_roles_to


def after_install():
	add_item_group()
	add_agriculture_analysis_criteria()


def after_sync():
	create_agriculture_roles()
	# set_default_certificate_print_format()
	add_all_roles_to("Administrator")

def add_item_group():
    for itemgroup in datadb.itemgroups:
        if not frappe.db.exists("Item Group", itemgroup.get("item_group_name")):
            frappe.get_doc(
				{
					"doctype": "Item Group",
					"item_group_name": itemgroup.get("item_group_name"),
					"is_group": itemgroup.get("is_group"),
					"parent_item_group": itemgroup.get("parent_item_group"),
				}
			).save()
        """ if not frappe.get_value("Item Group", itemgroup.get("item_group_name")):
            item_group = frappe.new_doc("Item Group")
            item_group.item_group_name = itemgroup.get("item_group_name")
            item_group.parent_item_group = _("All Item Groups")
            item_group.save() """

            
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
            
def create_agriculture_roles():
	create_agriculture_user_role()
	create_agriculture_manager_role()

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
