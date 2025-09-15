import click
import agriculture_management.datadb as datadb
import frappe
from frappe import _
from frappe.desk.page.setup_wizard.setup_wizard import add_all_roles_to


def after_install():
    click.echo("Installing Agriculture Customizations ...")
    add_item_group()
    # add_crop_category()
    add_warehouse()
    add_livestock_species()
    add_livestock_breeds_tunisia()
    add_agriculture_analysis_criteria()
    add_custom_fields_to_time_log()
    add_custom_fields_for_quality_inspection()
    company = frappe.defaults.get_user_default("Company")
    if company:
        setup_agriculture_assets(company)
    else:
        click.echo("WARNING: No default company found. Skipping asset setup.")


def after_sync():
    create_agriculture_roles()
    add_crop_category()
    # add_pest_categories()
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
            category.category_description = cropcategory.get(
                _("category_description"))
            category.save()


def add_pest_categories():
    frappe.get_doc(
        {
            "doctype": "Pest Categories",
            "pest_category_name": "Pest Categories Group",
            "is_group": 1,
            "is_main": 1,
            "parent_pest_categories": "",
        }
    ).save()
    for pestcategory in datadb.pestcategories:
        if not frappe.get_value("Pest Categories", pestcategory.get("pest_category_name")):
            category = frappe.new_doc("Pest Categories")
            category.name = pestcategory.get(_("pest_category_name"))
            category.is_group = pestcategory.get("is_group")
            category.pest_category_name = pestcategory.get(
                _("pest_category_name"))
            category.parent_pest_categories = pestcategory.get(
                _("parent_pest_categories"))
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


def add_livestock_species():
    for species in datadb.livestock_species:
        if not frappe.db.exists("Livestock Species", species.get("species_name")):
            frappe.get_doc(
                {
                    "doctype": "Livestock Species",
                    "species_name": species.get("species_name"),
                    "scientific_name": species.get("scientific_name"),
                    "gestation_period_days": species.get("gestation_period_days"),
                    "default_item_group": species.get("default_item_group"),
                }
            ).insert(ignore_permissions=True)
    click.echo("Livestock Species added ...")


def add_livestock_breeds_tunisia():
    for breed in datadb.livestock_breeds_tunisia:
        if not frappe.db.exists("Livestock Breed", breed.get("breed_name")):
            frappe.get_doc(
                {
                    "doctype": "Livestock Breed",
                    "breed_name": breed.get("breed_name"),
                    # Links to Livestock Species
                    "species": breed.get("species"),
                }
            ).save()
    click.echo("Livestock Breeds for Tunisia added ...")


def add_warehouse():
    """
    Creates standard Warehouse records for the agriculture module.
    This version correctly handles the tree structure by creating parents first.
    """
    # Get the default company for the site, as it's a mandatory field.
    default_company = frappe.defaults.get_user_default("company")
    if not default_company:
        all_companies = frappe.get_all("Company", fields=["name"], limit=1)
        if not all_companies:
            print("ERROR: No companies found in the system. Cannot create warehouses.")
            return
        default_company = all_companies[0].name

    print(f"Using company: {default_company}")

    # Loop 1: Create parents
    for wh in datadb.warehouses:
        if wh.get("parent_warehouse") is None:
            if not frappe.db.exists("Warehouse", {"warehouse_name": wh.get("warehouse_name")}):
                try:
                    frappe.get_doc({
                        "doctype": "Warehouse",
                        "warehouse_name": wh.get("warehouse_name"),
                        "is_group": wh.get("is_group"),
                        "company": default_company,
                    }).insert(ignore_permissions=True)
                    print(
                        f"Created parent warehouse: {wh.get('warehouse_name')}")
                except Exception as e:
                    print(
                        f"Error creating parent {wh.get('warehouse_name')}: {e}")
    frappe.db.commit()

    # Loop 2: Create children
    for wh in datadb.warehouses:
        if wh.get("parent_warehouse") is not None:
            if not frappe.db.exists("Warehouse", {"warehouse_name": wh.get("warehouse_name")}):
                try:
                    # --- THIS IS THE CRITICAL FIX ---
                    # Look up the full name of the parent warehouse.
                    parent_name = frappe.db.get_value(
                        "Warehouse", {"warehouse_name": wh.get("parent_warehouse")}, "name")

                    if not parent_name:
                        print(
                            f"Error: Could not find parent warehouse with warehouse_name '{wh.get('parent_warehouse')}' for child '{wh.get('warehouse_name')}'. Skipping.")
                        continue
                    # --- END OF FIX ---

                    frappe.get_doc({
                        "doctype": "Warehouse",
                        "warehouse_name": wh.get("warehouse_name"),
                        "is_group": wh.get("is_group"),
                        "parent_warehouse": parent_name,  # Use the correct, full name
                        "company": default_company,
                    }).insert(ignore_permissions=True)
                    print(
                        f"Created child warehouse: {wh.get('warehouse_name')}")
                except Exception as e:
                    print(
                        f"Error creating child {wh.get('warehouse_name')}: {e}")

    frappe.db.commit()
    print("Warehouse setup complete.")


def add_livestock_group_types():
    """
    Creates standard Livestock Group Type records if they do not already exist.
    """
    for group_type in datadb.group_types_to_create:
        # Check if a Group Type with this name already exists to prevent duplicates.
        if not frappe.db.exists("Group Type", group_type.get("group_type_name")):
            # If it doesn't exist, create a new document.
            doc = frappe.get_doc({
                "doctype": "Group Type",
                "main_group_type": group_type.get("main_group_type"),
                "group_type_name": group_type.get("group_type_name"),
            })
            doc.insert()
            print(f"Created Group Type: {group_type.get('group_type_name')}")

    print("Livestock Group Types setup complete.")


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
        custom_field.label = "Linked Crop Cycle"
        custom_field.fieldtype = "Link"
        custom_field.options = "Crop Cycle"  # The DocType to link to

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
        print(
            "Creating custom field 'custom_linked_sanitization_log' in Timesheet Detail...")

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
        click.echo(
            "Creating custom field 'custom_linked_quality_inspection' in Harvest Log...")
        custom_field = frappe.new_doc("Custom Field")
        custom_field.dt = "Harvest Log"
        custom_field.fieldname = "custom_linked_quality_inspection"
        custom_field.label = "Linked Quality Inspection"
        custom_field.fieldtype = "Link"
        custom_field.options = "Quality Inspection"
        custom_field.read_only = 1  # This field will be set by our script
        custom_field.insert_after = "status"
        custom_field.insert()


def setup_agriculture_assets(company):
    """
    Main function to orchestrate the creation of custom agriculture assets.
    """
    create_asset_categories(company)
    # You can add calls to other setup functions here if needed


def create_asset_categories(company):
    """
    Creates 'Hydroponic Systems' and 'Hydroponic Equipments' Asset Categories.
    This version uses the frappe.new_doc() and .append() pattern to correctly
    leverage the framework's internal logic, mimicking the provided example.
    """
    print(f"-> Creating Asset Categories for {company}...")

    try:
        # --- 1. Find the exact full account names using their unique numbers ---
        print("   - Finding required accounts by number...")
        accounts = {
            "systems_asset": get_account_name("2221", company),
            "equip_asset": get_account_name("2231", company),
            "accum_depr": get_account_name("282", company),
            "depr_expense": get_account_name("68112", company),
            "cwip": get_account_name("232", company)
        }

        # --- 2. Validate that all accounts were found before proceeding ---
        if not all(accounts.values()):
            print("   - CRITICAL: One or more required accounts could not be found. Aborting Asset Category creation.")
            return

        print("   - All required accounts found.")

        # --- 3. Prepare the data for the categories we want to create ---
        asset_categories_to_create = [
            {
                "category_name": "Hydroponic Systems",
                "fixed_asset_account": accounts["systems_asset"]
            },
            {
                "category_name": "Hydroponic Equipments",
                "fixed_asset_account": accounts["equip_asset"]
            }
        ]

        # --- 4. Loop through the data and create the categories ---
        for category_data in asset_categories_to_create:
            category_name = category_data.get("category_name")

            if frappe.db.exists("Asset Category", category_name):
                print(
                    f"   - Asset Category '{category_name}' already exists. Skipping.")
                continue

            # Create an empty document in memory
            doc = frappe.new_doc("Asset Category")
            doc.asset_category_name = category_name

            # Append the child table row with all the account details
            doc.append("accounts", {
                "company_name": company,
                "fixed_asset_account": category_data.get("fixed_asset_account"),
                "accumulated_depreciation_account": accounts["accum_depr"],
                "depreciation_expense_account": accounts["depr_expense"],
                "capital_work_in_progress_account": accounts["cwip"]
            })

            # Insert the complete document (parent + child) into the database
            doc.insert(ignore_permissions=True)
            print(f"   - Created Asset Category: {category_name}")

        frappe.db.commit()

    except Exception as e:
        print(
            f"-> ERROR while creating asset categories for {company}. Error: {e}")
        frappe.log_error(frappe.get_traceback(), "Asset Category Setup Failed")


# Ensure you have this helper function in your file
def get_account_name(account_number, company):
    """
    Fetches the full account name from the database based on its number and company.
    """
    try:
        account_name = frappe.db.get_value(
            "Account", {"account_number": account_number, "company": company}, "name")
        if not account_name:
            print(
                f"  -> WARNING: Could not find account with number '{account_number}' for company '{company}'.")
        return account_name
    except Exception as e:
        print(
            f"  -> ERROR querying for account number '{account_number}': {e}")
        return None
