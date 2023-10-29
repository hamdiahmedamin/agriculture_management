import agriculture_management.datadb as datadb
import frappe


def before_uninstall():
    delete_agriculture_item_group()
    delete_agriculture_roles()


def delete_agriculture_item_group():
	for itemgroup in datadb.itemgroups:
		if frappe.db.exists("Item Group", itemgroup.get("item_group_name")):
			frappe.db.delete("Item Group", itemgroup)

def delete_agriculture_roles():
	roles = ["Agriculture User", "Agriculture Manager"]
	for role in roles:
		if frappe.db.exists("Role", role):
			frappe.db.delete("Role", role)