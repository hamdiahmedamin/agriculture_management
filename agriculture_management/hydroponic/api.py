# Final api.py - Corrects the Company AttributeError

import frappe
from frappe.utils import flt, cint
from frappe import _
import json


@frappe.whitelist()
def create_bom_from_recipe(recipe_name, dialog_values):
    """
    API endpoint to create a BOM from a Nutrient Recipe.
    This version correctly sources the Company from the user's default settings.
    """
    try:
        # Immediately parse the incoming JSON string into a dictionary.
        if isinstance(dialog_values, str):
            dialog_values = json.loads(dialog_values)

        # Get the default group from the custom settings DocType.
        default_group = frappe.db.get_single_value(
            'Hydroponics Settings', 'default_group_for_stock_solutions')
        if not default_group:
            frappe.throw(
                "Please set the 'Default Group for Stock Solutions' in Hydroponics Settings first.")

        recipe = frappe.get_doc('Nutrient Recipe', recipe_name)
        item_name = dialog_values['item_name']

        # Create the Item if it does not exist
        if not frappe.db.exists('Item', item_name):
            finished_item = frappe.new_doc('Item')
            finished_item.item_code = item_name
            finished_item.item_name = item_name
            finished_item.item_group = default_group
            finished_item.stock_uom = dialog_values['uom']
            finished_item.is_stock_item = 1
            finished_item.has_bom = 1
            finished_item.save(ignore_permissions=True)
            frappe.msgprint(f"Created new Item: {finished_item.name}")

        # --- FIX IS HERE ---
        # A BOM must belong to a company. We get it from the user's defaults.
        company = frappe.defaults.get_user_default("company")
        if not company:
            frappe.throw(
                "No default Company found for the current user. Please set one in User Settings.")

        # Create the new BOM document.
        bom = frappe.new_doc('BOM')
        bom.item = item_name
        bom.quantity = flt(dialog_values['batch_size'])
        bom.uom = dialog_values['uom']
        bom.company = company  # Assign the fetched company here
        bom.is_active = 1

        # Add ingredients to the BOM
        for ingredient in recipe.ingredients:
            if ingredient.stock_tank_id == dialog_values['stock_tank']:
                required_qty = (flt(ingredient.quantity) / flt(
                    ingredient.base_stock_volume)) * flt(dialog_values['batch_size'])
                bom.append('items', {
                    'item_code': ingredient.ingredient,
                    'qty': required_qty,
                    'uom': ingredient.quantity_uom,
                    'source_warehouse': dialog_values['source_warehouse']
                })

        if not bom.items:
            frappe.throw(
                f"No ingredients found in the recipe for Stock Tank <b>{dialog_values['stock_tank']}</b>.")

        bom.insert(ignore_permissions=True)

        return {"bom_name": bom.name}

    except Exception as e:
        frappe.log_error(frappe.get_traceback(),
                         'BOM Creation From Recipe Failed')
        frappe.throw(f"An error occurred during BOM creation: {e}")


@frappe.whitelist()
def get_item_default_warehouse(item_code, company):
    """
    Safely fetches the default warehouse from an Item's 'Item Default' child table.
    This whitelisted function can be called from the client side.

    :param item_code: The Item Code to look up.
    :param company: The Company to filter the defaults by.
    :return: The default warehouse name, or None if not found.
    """
    if not item_code or not company:
        return None

    # This is a direct database query that is very efficient.
    # It looks inside the `tabItem Default` table for a matching row.
    warehouse = frappe.db.get_value(
        "Item Default",
        filters={
            "parent": item_code,
            "parenttype": "Item",
            "company": company
        },
        fieldname="default_warehouse"
    )

    return warehouse


@frappe.whitelist()
def run_maintenance_report(filters=None):
    """
    A whitelisted function that runs the Maintenance & Compliance Schedule report's
    get_data function and returns the result. This can be safely called from a Server Script.
    """
    if not filters:
        filters = {}

    # Get the Python function for the Maintenance Report using the full, unrestricted API
    report_get_data_func = frappe.get_attr(
        "agriculture_management.hydroponic.report.maintenance_&_compliance_schedule.maintenance_&_compliance_schedule.get_data"
    )

    # Run the function and return its data
    report_data = report_get_data_func(filters)
    return report_data


@frappe.whitelist()
def check_hydroponic_system_for_zones(asset_name):
    """
    Checks if a given Hydroponic System (Asset) has any Growing Zones linked to it.
    Returns a dictionary with the status and count.
    """
    if not asset_name:
        return {"has_zones": False, "zone_count": 0}

    # frappe.db.count is a very efficient way to check for existence
    zone_count = frappe.db.count(
        "Growing Zone", {"hydroponic_system": asset_name})

    return {
        "has_zones": zone_count > 0,
        "zone_count": zone_count
    }


@frappe.whitelist()
def get_zones_for_system(asset_name):
    """
    Fetches all Growing Zones linked to a specific Hydroponic System (Asset).
    Returns a list of documents ready to be inserted into a child table.
    """
    if not asset_name:
        return []

    # We fetch the 'name' of the Growing Zone but alias it as 'growing_zone'
    # This directly matches the fieldname in the 'growing_zones' child table in Crop Cycle,
    # which makes the client-side code much simpler.
    return frappe.get_all(
        "Growing Zone",
        filters={"hydroponic_system": asset_name},
        fields=["name as growing_zone"]  # This alias is key for simplicity
    )


@frappe.whitelist()
def delete_zones_for_system(asset_name):
    """
    Deletes all Growing Zones linked to a specific Hydroponic System (Asset).
    WARNING: This is a destructive operation.
    """
    linked_zones = frappe.get_all("Growing Zone", filters={
                                  "hydroponic_system": asset_name}, fields=["name"])

    if not linked_zones:
        return 0

    # We must first check if any of these zones are linked to active Crop Cycles
    active_links = frappe.get_all("Crop Cycle Zone",
                                  filters={"growing_zone": (
                                      "in", [z.name for z in linked_zones])},
                                  fields=["parent"]
                                  )
    if active_links:
        linked_cycles = ", ".join(
            list(set([link.parent for link in active_links])))
        frappe.throw(
            _("Cannot delete existing zones because they are linked to active Crop Cycles: {0}. Please remove them from the Crop Cycles first.").format(
                linked_cycles)
        )

    count = 0
    for zone in linked_zones:
        frappe.delete_doc("Growing Zone", zone.name,
                          ignore_permissions=True, force=True)
        count += 1

    frappe.db.commit()  # Commit after all deletions are done
    return count


@frappe.whitelist()
def apply_zone_layout_to_asset(asset_name, layout_config, mode):
    """
    A single, transactional function to apply a new zone layout to a Hydroponic System Asset.
    :param asset_name: The name of the Asset to modify.
    :param layout_config: A dict with keys like 'naming_prefix', 'num_racks', etc.
    :param mode: Either 'overwrite' or 'append'.
    """
    if isinstance(layout_config, str):
        layout_config = json.loads(layout_config)
    # --- 1. VALIDATION ---
    if mode not in ['overwrite', 'append']:
        frappe.throw(
            _("Invalid operation mode specified. Must be 'overwrite' or 'append'."))

    try:
        racks = cint(layout_config.get('num_racks'))
        tiers = cint(layout_config.get('num_tiers'))
        gullies = cint(layout_config.get('num_gullies'))
        capacity = cint(layout_config.get('capacity_per_gully'))
        prefix = layout_config.get('naming_prefix')
        if not all([racks > 0, tiers > 0, gullies > 0, capacity >= 0]):
            frappe.throw(
                _("Rack, Tier, and Gully counts must be greater than zero."))
    except (ValueError, TypeError):
        frappe.throw(_("Please enter valid whole numbers for the layout."))

    # --- 2. DELETION (if in overwrite mode) ---
    if mode == 'overwrite':
        # Assuming this helper function exists
        deleted_count = delete_zones_for_system(asset_name)

    # --- 3. ZONE GENERATION ---
    required_zone_names = set()
    for r in range(1, racks + 1):
        for t in range(1, tiers + 1):
            for g in range(1, gullies + 1):
                zone_name = f"{prefix or 'Rack'} {r} - Tier {t} - Gully {g}"
                required_zone_names.add(zone_name)

    existing_zones_for_system = frappe.get_all(
        "Growing Zone", filters={"hydroponic_system": asset_name}, fields=["zone_name"])
    existing_zone_names = {z.zone_name for z in existing_zones_for_system}
    zones_to_create = sorted(list(required_zone_names - existing_zone_names))

    created_count = 0
    if zones_to_create:
        # --- THIS IS THE FIX: Replaced frappe.insert_many ---
        # --- 4. BULK CREATION (Backward-Compatible Method) ---
        try:
            # Loop through the list of zone names and create a doc for each one
            for zone_name in zones_to_create:
                new_zone = frappe.get_doc({
                    "doctype": "Growing Zone",
                    "zone_name": zone_name,
                    "hydroponic_system": asset_name,
                    "zone_type": "NFT Gully",
                    "status": "Active",
                    "plant_capacity": capacity
                })
                new_zone.insert(ignore_permissions=True)
                created_count += 1
        except Exception as e:
            frappe.db.rollback()  # Rollback if any insertion fails
            frappe.log_error(message=str(
                e), title="Growing Zone Generation Failed")
            frappe.throw(
                _("An error occurred during bulk creation of Growing Zones. Please check the Error Log."))
        # --- END OF FIX ---

    # --- 5. SAVE CONFIGURATION BACK TO ASSET ---
    frappe.db.set_value("Asset", asset_name, {
        "custom_naming_prefix": prefix,
        "custom_number_of_racks": racks,
        "custom_tiers_per_rack": tiers,
        "custom_gullies_per_tier": gullies,
        "custom_capacity_per_gully": capacity
    })

    # --- 6. COMMIT & RETURN FEEDBACK ---
    frappe.db.commit()

    # ... (The return message logic remains the same) ...
    if mode == 'overwrite':
        message = _("Successfully reset and created {0} new zones.").format(
            created_count)
    elif created_count > 0:
        message = _("Successfully appended {0} new zones.").format(
            created_count)
    else:
        message = _(
            "Layout updated, but no new zones were needed as they already exist.")

    return {"created_count": created_count, "message": message}
