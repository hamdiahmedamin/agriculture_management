# File: apps/your_custom_app/your_custom_app/patches/v0_1/add_harvest_log_to_qi_reference.py

import frappe

def execute():
	"""
	This migration script directly modifies the 'Quality Inspection' DocType
	to add 'Harvest Log' as an option in the 'reference_type' field.
	"""
	print("\nRunning patch: Adding 'Harvest Log' to Quality Inspection reference types...")
	
	# Fetch the 'Property Setter' DocType, which is used to modify standard DocTypes.
	# This is safer than modifying the DocType directly.
	frappe.reload_doc("quality_management", "doctype", "quality_inspection")
	
	# Find the 'reference_type' field within the Quality Inspection DocType.
	meta = frappe.get_meta("Quality Inspection")
	reference_type_field = meta.get_field("reference_type")
	
	if reference_type_field:
		# Get the current list of options. It's a string with newlines.
		current_options = reference_type_field.options.split("\n")
		
		# Check if 'Harvest Log' is already in the list to prevent duplicates.
		if "Harvest Log" not in current_options:
			# Add our new option to the list.
			current_options.append("Harvest Log")
			
			# Join the list back into a single string with newlines.
			new_options = "\n".join(current_options)
			
			# Create a Property Setter to apply the change.
			frappe.make_property_setter({
				"doctype": "Quality Inspection",
				"fieldname": "reference_type",
				"property": "options",
				"value": new_options
			})
			print("   ...Success: 'Harvest Log' option added.")
		else:
			print("   ...Skipped: 'Harvest Log' option already exists.")
	else:
		print("   ...Failed: Could not find the 'reference_type' field in Quality Inspection.")