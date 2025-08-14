# # File: apps/your_custom_app/your_custom_app/setup_scripts/force_add_qi_option.py

# import frappe

# def run():
# 	"""
# 	This script directly modifies the 'Quality Inspection' DocType's options.
# 	It uses the most direct method available.
# 	"""
# 	doc_name = "Quality Inspection"
# 	field_name = "reference_type"
# 	option_to_add = "Harvest Log"

# 	print(f"--- Forcefully updating options for {doc_name} -> {field_name} ---")

# 	try:
# 		# Method 1: The Standard Property Setter
# 		# We try this first as it's the 'cleanest' way.
# 		meta = frappe.get_meta(doc_name)
# 		field = meta.get_field(field_name)
		
# 		if not field:
# 			print(f"ERROR: Field '{field_name}' not found in DocType '{doc_name}'. Aborting.")
# 			return

# 		current_options = field.options or ""
# 		options_list = [opt.strip() for opt in current_options.split('\n') if opt.strip()]

# 		if option_to_add not in options_list:
# 			print(f"'{option_to_add}' not found in options. Attempting to add via Property Setter...")
# 			options_list.append(option_to_add)
# 			new_options = "\n".join(options_list)
			
# 			frappe.make_property_setter({
# 				"doctype": doc_name,
# 				"fieldname": field_name,
# 				"property": "options",
# 				"value": new_options,
# 			})
# 			print("   ...Property Setter created successfully.")
# 		else:
# 			print(f"'{option_to_add}' already exists in options. No changes made by Property Setter.")

# 		# Method 2: The "Brute Force" Direct Database Update
# 		# This is a fallback. We check if the Property Setter actually worked.
# 		# If not, we update the core DocType definition directly.
# 		# This is generally discouraged, but necessary if the system is being stubborn.
		
# 		frappe.db.commit() # Commit the property setter transaction
# 		frappe.clear_cache(doctype=doc_name) # Clear cache to read the latest state
		
# 		meta = frappe.get_meta(doc_name)
# 		field = meta.get_field(field_name)
# 		current_options_after_setter = field.options or ""
# 		options_list_after_setter = [opt.strip() for opt in current_options_after_setter.split('\n') if opt.strip()]

# 		if option_to_add not in options_list_after_setter:
# 			print("WARNING: Property Setter did not take effect. Attempting direct DB update...")
			
# 			# We need to get the original options from the core DocField
# 			original_options_str = frappe.db.get_value("DocField", {"parent": doc_name, "fieldname": field_name}, "options")
# 			original_options_list = [opt.strip() for opt in original_options_str.split('\n') if opt.strip()]
			
# 			if option_to_add not in original_options_list:
# 				original_options_list.append(option_to_add)
# 				final_options = "\n".join(original_options_list)
				
# 				frappe.db.set_value("DocField", {"parent": doc_name, "fieldname": field_name}, "options", final_options)
# 				frappe.db.commit()
# 				print("   ...Direct DB update successful.")
# 			else:
# 				print("   ...Option exists in core DocField. No changes made.")

# 		# Final verification
# 		frappe.clear_cache(doctype=doc_name)
# 		meta = frappe.get_meta(doc_name)
# 		final_field = meta.get_field(field_name)
# 		if option_to_add in (final_field.options or ""):
# 			print(f"--- VERIFICATION SUCCESS: '{option_to_add}' is now in the options for {doc_name}. ---")
# 		else:
# 			print(f"--- VERIFICATION FAILED: Could not add '{option_to_add}' to the options. ---")

# 	except Exception as e:
# 		print(f"An error occurred: {e}")