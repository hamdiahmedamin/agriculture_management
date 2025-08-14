      
import frappe
from frappe.utils import get_link_to_form, nowdate


# The @frappe.whitelist() decorator is ESSENTIAL.
# It makes this function callable from the client-side JavaScript.
@frappe.whitelist()
def get_gestation_period(species):
    """
    API function to fetch the gestation period in days for a given species.
    
    :param species: The name of the Livestock Species DocType.
    :return: An integer representing the gestation period in days.
    """
    if not species:
        return 0
    
    try:
        # frappe.db.get_value is a fast and safe way to get a single field value
        # from another DocType.
        gestation_days = frappe.db.get_value(
            "Livestock Species",      # The DocType to query
            species,                  # The specific document name to look for
            "gestation_period_days"   # The field name to fetch
        )
        return int(gestation_days) if gestation_days else 0
    except Exception as e:
        frappe.log_error(f"Error fetching gestation period: {e}")
        return 0
    
@frappe.whitelist()
def move_livestock_group(group_name, new_location):
    """
    Creates a Material Transfer Stock Entry to move all serialized animals
    from a Livestock Group to a new location (Warehouse).
    """
    try:
        group = frappe.get_doc("Livestock Group", group_name)
        from_location = group.group_location

        if not from_location:
            frappe.throw("The Livestock Group must have a current Location set.")

        # Create a new Stock Entry document
        se = frappe.new_doc("Stock Entry")
        se.stock_entry_type = "Material Transfer"
        se.set_posting_date = True # Use current date and time
        
        # This is for display and reference
        se.purpose = "Material Transfer" 
        se.from_warehouse = from_location
        se.to_warehouse = new_location

        items_to_move = 0
        for animal_row in group.animal_list:
            animal = frappe.get_doc("Livestock", animal_row.animal)
            # IMPORTANT: We can only move animals that are tracked in inventory
            if animal.serial_no and animal.item_code:
                se.append("items", {
                    "item_code": animal.item_code,
                    "serial_no": animal.serial_no,
                    "qty": 1,
                    "s_warehouse": from_location,
                    "t_warehouse": new_location,
                    "uom": animal.uom or "Nos" # Default to 'Nos' if not set
                })
                items_to_move += 1
        
        if not items_to_move:
            frappe.throw("No serialized animals found in this group to move.")

        # Insert and submit the stock transaction
        se.insert()
        se.submit()

        # Finally, update the group's location
        group.location = new_location
        group.save()

        return se.name # Return the name of the new Stock Entry
        
    except Exception as e:
        frappe.log_error(frappe.get_traceback(), "Livestock Group Move Error")
        frappe.throw(str(e))
    
# This function is called by the hook, not directly from JS, so it doesn't need @frappe.whitelist()
def update_livestock_status_on_sale(doc, method):
    """
    Loops through items in a submitted Sales Invoice. If an Asset is being sold,
    it finds the corresponding Livestock document and updates its status.
    'doc' is the Sales Invoice document.
    """
    for item in doc.items:
        if item.asset:
            # Check if a Livestock document is linked to this Asset
            livestock_name = frappe.db.get_value(
                "Livestock",
                {"asset": item.asset},
                "name" # Get the name (ID) of the livestock document
            )

            if livestock_name:
                try:
                    # Load the document, change status, and save
                    livestock_doc = frappe.get_doc("Livestock", livestock_name)
                    livestock_doc.status = "Sold"
                    livestock_doc.save(ignore_permissions=True) # Ignore perms because this is an automated action
                    frappe.msgprint(f"Status for Livestock {livestock_name} updated to Sold.")
                except Exception as e:
                    frappe.log_error(f"Failed to update status for Livestock {livestock_name}: {e}")

def sync_livestock_location_on_move(doc, method):
    """
    If a Stock Entry is a Material Transfer, finds the corresponding
    Livestock document for each Serial No and updates its location.
    'doc' is the Stock Entry document.
    """
    if doc.stock_entry_type == "Material Transfer":
        for item in doc.items:
            if item.serial_no:
                # Find the livestock doc linked to this serial number
                livestock_name = frappe.db.get_value(
                    "Livestock",
                    {"serial_no": item.serial_no},
                    "name"
                )

                if livestock_name:
                    try:
                        # Update the location_pen field with the target warehouse
                        frappe.db.set_value(
                            "Livestock", 
                            livestock_name, 
                            "location_pen", 
                            item.t_warehouse
                        )
                    except Exception as e:
                        frappe.log_error(f"Failed to update location for Livestock {livestock_name}: {e}")
                    
@frappe.whitelist()
def create_serial_no_for_livestock(doc_name):
    """
    Creates and submits a Serial No document based on data from a Livestock doc.
    """
    livestock = frappe.get_doc("Livestock", doc_name)

    if not livestock.item_code or not livestock.location_pen:
        frappe.throw("Please set the 'Item Code' and 'Location / Pen' before creating a Serial No.")

    if frappe.db.exists("Serial No", livestock.animal_id_tag_id):
        return livestock.animal_id_tag_id # Return existing if it's already there

    try:
        sn = frappe.new_doc("Serial No")
        # Use the Tag ID as the name of the Serial No for easy lookup
        sn.serial_no = livestock.animal_id_tag_id 
        sn.item_code = livestock.item_code
        sn.warehouse = livestock.location_pen
        sn.insert()
        return sn.name
    except Exception as e:
        frappe.log_error(frappe.get_traceback())
        frappe.throw(str(e))

def handle_livestock_status_change(doc, method):
    """
    Main handler called on livestock update. Checks if status change requires action.
    """
    inactive_statuses = ["Deceased", "Culled"]
    
    # doc.get_doc_before_save() gets the document's state before this current save
    doc_before_save = doc.get_doc_before_save()
    if not doc_before_save:
        return

    # Trigger only if the status has CHANGED to an inactive one
    if doc.status != doc_before_save.status and doc.status in inactive_statuses:
        if doc.asset:
            try:
                create_asset_disposal_entry(doc)
            except Exception as e:
                frappe.log_error(frappe.get_traceback())
                frappe.msgprint(f"Failed to create asset disposal entry for {doc.asset}: {e}")

def create_asset_disposal_entry(livestock_doc):
    """
    Creates a Journal Entry to write off the value of a scrapped/deceased asset.
    """
    asset_doc = frappe.get_doc("Asset", livestock_doc.asset)
    
    # Do not proceed if asset is already disposed or scrapped
    if asset_doc.status in ["Disposed", "Scrapped"]:
        return

    settings = frappe.get_doc("Livestock Settings")
    # Validate that settings are configured
    if not all([settings.asset_disposal_expense_account, settings.default_fixed_asset_account, settings.default_accumulated_depreciation_account]):
        frappe.throw("Please configure all Asset Disposal accounts in Livestock Settings.")

    # Get key values from the Asset
    gross_value = asset_doc.gross_purchase_amount
    accumulated_depreciation = asset_doc.accumulated_depreciation_amount
    net_book_value = gross_value - accumulated_depreciation

    # Create the Journal Entry
    je = frappe.new_doc("Journal Entry")
    je.voucher_type = "Journal Entry"
    je.posting_date = nowdate()
    je.user_remark = f"Disposal of Asset {asset_doc.name} for deceased/culled Livestock {livestock_doc.name}"

    # Add the accounting entries (the lines)
    je.append("accounts", {
        "account": settings.default_accumulated_depreciation_account,
        "debit_in_account_currency": accumulated_depreciation,
        "party_type": "Asset",
        "party": asset_doc.name
    })
    je.append("accounts", {
        "account": settings.asset_disposal_expense_account,
        "debit_in_account_currency": net_book_value,
        "party_type": "Asset",
        "party": asset_doc.name
    })
    je.append("accounts", {
        "account": settings.default_fixed_asset_account,
        "credit_in_account_currency": gross_value,
        "party_type": "Asset",
        "party": asset_doc.name
    })

    je.insert(ignore_permissions=True)
    je.submit()

    # Update the asset status
    asset_doc.status = "Scrapped"
    asset_doc.save()

    frappe.msgprint(f"Created Journal Entry {get_link_to_form('Journal Entry', je.name)} for asset disposal.", indicator="green")

@frappe.whitelist()
def create_herd_snapshot(livestock_group_name):
    """
    Creates a snapshot of a Livestock Group's current state.
    """
    group = frappe.get_doc("Livestock Group", livestock_group_name)

    snapshot = frappe.new_doc("Herd Snapshot")
    snapshot.livestock_group = group.name
    snapshot.snapshot_date = nowdate()

    total_value = 0.0
    total_age = 0.0
    animal_count = len(group.animal_list)

    for animal_row in group.animal_list:
        animal = frappe.get_doc("Livestock", animal_row.animal)
        asset_value = 0.0
        if animal.asset:
            # Get the current book value of the linked asset
            asset_value = frappe.db.get_value("Asset", animal.asset, "value_after_depreciation") or 0.0

        snapshot.append("snapshot_animal_list", {
            "livestock": animal.name,
            "age_at_snapshot": animal.age,
            "asset_value_at_snapshot": asset_value
        })
        total_value += asset_value
        total_age += animal.age

    # Set summary header fields
    snapshot.total_animals = animal_count
    snapshot.total_asset_value = total_value
    snapshot.average_age = round(total_age / animal_count, 2) if animal_count else 0.0

    snapshot.insert(ignore_permissions=True)
    return snapshot.name # Return the new doc's name to the client

@frappe.whitelist(allow_guest=True)
def log_device_data(data, source_device):
    """
    API endpoint for external devices to post data.
    Note: In production, you MUST add an API key/secret for authentication.
    """
    try:
        log = frappe.new_doc("Device Integration Log")
        log.source_device = source_device
        log.payload = frappe.as_json(data)
        log.status = "Unprocessed"
        log.insert(ignore_permissions=True)
        frappe.db.commit() # Commit immediately as this is an API call
        return {"status": "success", "message": f"Log created for device {source_device}"}
    except Exception:
        frappe.log_error(title="Device Integration API Error")
        frappe.db.rollback()
        return {"status": "error", "message": "Failed to create log"}
    
@frappe.whitelist(allow_guest=True)
def get_total_herd_asset_value(doctype, name):
    """
    Calculates the sum of 'value_after_depreciation' for all Assets linked
    to active Livestock records.
    
    This function is specifically designed to be called by a Number Card.
    The 'doctype' and 'name' arguments are passed by the framework but are not used in this global calculation.
    """
    
    # First, get a list of all asset names linked to active livestock
    asset_list = frappe.get_all("Livestock",
        filters={
            "status": "Active",
            "is_asset": 1,
            "asset": ("is", "set")
        },
        pluck="asset"
    )

    if not asset_list:
        return 0.0

    # Now, sum the value_after_depreciation for only those assets
    total_value = frappe.db.sql("""
        SELECT SUM(value_after_depreciation)
        FROM `tabAsset`
        WHERE name IN %(assets)s
    """, {"assets": tuple(asset_list)})

    # Safely extract the single value from the SQL result
    if total_value and total_value[0] and total_value[0][0]:
        return float(total_value[0][0])
    else:
        return 0.0
    
@frappe.whitelist()
def get_animal_genealogy(animal_id):
    """
    Fetches the genealogy (ancestors) for a given animal and formats it
    for Frappe's OrgChart. We are building the tree upwards from the child.
    """
    if not frappe.db.exists("Livestock", animal_id):
        return {}

    # Get all relevant animal data in one query for efficiency
    all_animals = frappe.get_all("Livestock", fields=["name", "animal_name", "sire_father", "dam_mother"])
    
    # Create a dictionary for quick lookups
    animal_map = {d.name: d for d in all_animals}

    def build_ancestor_tree(doc_name):
        # Base case: if animal not in our map, stop.
        if doc_name not in animal_map:
            return None

        animal_data = animal_map[doc_name]
        
        # The node structure Frappe's OrgChart expects: { name, title, children }
        node = {
            "name": animal_data.name,
            "title": animal_data.animal_name or animal_data.name # Display name
        }

        # Recursive step: Find parents and build their sub-trees
        parents = []
        if animal_data.sire_father:
            parent_node = build_ancestor_tree(animal_data.sire_father)
            if parent_node:
                parents.append(parent_node)

        if animal_data.dam_mother:
            parent_node = build_ancestor_tree(animal_data.dam_mother)
            if parent_node:
                parents.append(parent_node)
        
        if parents:
            node["children"] = parents # The chart sees ancestors as "children" in the data structure
        
        return node

    return build_ancestor_tree(animal_id)

import frappe

import frappe

@frappe.whitelist()
def get_offspring_and_mates(animal_id):
    """
    Finds all direct offspring for a given animal_id and determines the mate
    (the other parent) for each offspring.
    This definitive version uses a direct SQL query and manually converts the
    result to a standard dict to bypass a framework serialization bug.
    """
    if not animal_id:
        return []

    # The SQL query is correct.
    children_data = frappe.db.sql("""
        SELECT
            name, sire_father, dam_mother, date_of_birth, gender
        FROM
            `tabLivestock`
        WHERE
            status = 'Active' AND (sire_father = %(animal_id)s OR dam_mother = %(animal_id)s)
        ORDER BY
            date_of_birth DESC
    """, {"animal_id": animal_id}, as_dict=True)

    # --- THIS IS THE DEFINITIVE FIX ---
    # Manually convert each item in the result to a standard Python dictionary.
    children = [dict(row) for row in children_data]
    # --- END OF FIX ---

    offspring_list = []
    for child in children:
        mate = None
        # This logic is correct and will now work because the JSON will be correct.
        if child.get("sire_father") == animal_id:
            mate = child.get("dam_mother")
        elif child.get("dam_mother") == animal_id:
            mate = child.get("sire_father")
        
        offspring_list.append({
            "offspring": child.get("name"),
            "mate": mate,
            "date_of_birth": child.get("date_of_birth"),
            "gender": child.get("gender")
        })

    return offspring_list