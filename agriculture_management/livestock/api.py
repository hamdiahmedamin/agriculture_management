
import frappe
import json
from frappe.utils import get_link_to_form, nowdate, get_datetime, getdate, flt
from dateutil.relativedelta import relativedelta

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
            frappe.throw(
                "The Livestock Group must have a current Location set.")

        # Create a new Stock Entry document
        se = frappe.new_doc("Stock Entry")
        se.stock_entry_type = "Material Transfer"
        se.set_posting_date = True  # Use current date and time

        # This is for display and reference
        se.purpose = "Material Transfer"
        se.from_warehouse = from_location
        se.to_warehouse = new_location

        items_to_move = 0
        for animal_row in group.animal_list:
            animal = frappe.get_doc("Animal", animal_row.animal)
            # IMPORTANT: We can only move animals that are tracked in inventory
            if animal.serial_no and animal.item_code:
                se.append("items", {
                    "item_code": animal.item_code,
                    "serial_no": animal.serial_no,
                    "qty": 1,
                    "s_warehouse": from_location,
                    "t_warehouse": new_location,
                    "uom": animal.uom or "Nos"  # Default to 'Nos' if not set
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

        return se.name  # Return the name of the new Stock Entry

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
                "Animal",
                {"asset": item.asset},
                "name"  # Get the name (ID) of the livestock document
            )

            if livestock_name:
                try:
                    # Load the document, change status, and save
                    livestock_doc = frappe.get_doc("Animal", livestock_name)
                    livestock_doc.status = "Sold"
                    # Ignore perms because this is an automated action
                    livestock_doc.save(ignore_permissions=True)
                    frappe.msgprint(
                        f"Status for Livestock {livestock_name} updated to Sold.")
                except Exception as e:
                    frappe.log_error(
                        f"Failed to update status for Livestock {livestock_name}: {e}")


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
                    "Animal",
                    {"serial_no": item.serial_no},
                    "name"
                )

                if livestock_name:
                    try:
                        # Update the location_pen field with the target warehouse
                        frappe.db.set_value(
                            "Animal",
                            livestock_name,
                            "location_pen",
                            item.t_warehouse
                        )
                    except Exception as e:
                        frappe.log_error(
                            f"Failed to update location for Livestock {livestock_name}: {e}")


@frappe.whitelist()
def create_serial_no_for_livestock(doc_name):
    """
    Creates and submits a Serial No document based on data from a Livestock doc.
    """
    livestock = frappe.get_doc("Animal", doc_name)

    if not livestock.item_code or not livestock.location_pen:
        frappe.throw(
            "Please set the 'Item Code' and 'Location / Pen' before creating a Serial No.")

    if frappe.db.exists("Serial No", livestock.animal_id_tag_id):
        return livestock.animal_id_tag_id  # Return existing if it's already there

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
                frappe.msgprint(
                    f"Failed to create asset disposal entry for {doc.asset}: {e}")


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
        frappe.throw(
            "Please configure all Asset Disposal accounts in Livestock Settings.")

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

    frappe.msgprint(
        f"Created Journal Entry {get_link_to_form('Journal Entry', je.name)} for asset disposal.", indicator="green")


@frappe.whitelist()
def create_herd_snapshot(livestock_group_name):
    """
    Creates and inserts a new Herd Snapshot document.
    The document's own controller (before_insert) will handle all the data population.
    """
    try:
        snapshot = frappe.new_doc("Herd Snapshot")
        snapshot.livestock_group = livestock_group_name
        # The date is set by default in the DocType, no need to set it here
        snapshot.insert(ignore_permissions=True)
        return snapshot.name
    except Exception as e:
        frappe.log_error(frappe.get_traceback())
        frappe.throw(f"Failed to create Herd Snapshot. Server error: {e}")


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
        frappe.db.commit()  # Commit immediately as this is an API call
        return {"status": "success", "message": f"Log created for device {source_device}"}
    except Exception:
        frappe.log_error(title="Device Integration API Error")
        frappe.db.rollback()
        return {"status": "error", "message": "Failed to create log"}


@frappe.whitelist(allow_guest=True)
def get_total_herd_asset_value(doctype=None, name=None, filters=None):
    """
    Calculates the sum of 'value_after_depreciation' for all Assets linked
    to active Livestock records.

    This function is specifically designed to be called by a Number Card.
    The 'doctype' and 'name' arguments are passed by the framework but are not used in this global calculation.
    """

    # First, get a list of all asset names linked to active livestock
    asset_list = frappe.get_all("Animal",
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
    if not frappe.db.exists("Animal", animal_id):
        return {}

    # Get all relevant animal data in one query for efficiency
    all_animals = frappe.get_all(
        "Animal", fields=["name", "animal_name", "sire_father", "dam_mother"])

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
            "title": animal_data.animal_name or animal_data.name  # Display name
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
            # The chart sees ancestors as "children" in the data structure
            node["children"] = parents

        return node

    return build_ancestor_tree(animal_id)


@frappe.whitelist()
def get_offspring_and_mates(animal_id):
    """
    Finds all direct offspring for a given animal_id and determines the mate
    (the other parent) for each offspring.
    This is the correct, definitive version.
    """
    if not animal_id:
        return []

    children_data = frappe.db.sql("""
        SELECT
            name, sire_father, dam_mother, date_of_birth, gender
        FROM
            `tabAnimal`
        WHERE
            status = 'Active' AND (sire_father = %(animal_id)s OR dam_mother = %(animal_id)s)
        ORDER BY
            date_of_birth DESC
    """, {"animal_id": animal_id}, as_dict=True)

    # Convert to standard dict to be safe
    children = [dict(row) for row in children_data]

    offspring_list = []
    for child in children:
        mate = None
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


@frappe.whitelist()
def get_animal_health_history(animal_id):
    """
    Fetches a complete, sorted health history for a single animal.
    This final version returns data structured for a paginated grid with Dynamic Links.
    """
    if not animal_id:
        return []

    # --- Step 1: Fetch Individual Records ---
    treatments = frappe.get_all(
        "Treatment Record",
        filters={"animal": animal_id, "docstatus": ["!=", 2]},
        fields=["name as record", "date_of_treatment as date",
                "disease as details", "status"]
    )
    for t in treatments:
        t["event_type"] = "Individual Treatment"
        t["record_type"] = "Treatment Record"

    vaccinations = frappe.get_all(
        "Vaccination Record",
        filters={"animal": animal_id, "docstatus": ["!=", 2]},
        fields=["name as record", "date",
                "vaccination_against as details", "'Completed' as status"]
    )
    for v in vaccinations:
        v["event_type"] = "Individual Vaccination"
        v["record_type"] = "Vaccination Record"

    # --- Step 2: Fetch Group Events Where This Animal Participated ---
    participated_events = frappe.get_all(
        "Animal List",
        filters={"animal": animal_id, "parenttype": [
            "in", ["Group Treatment", "Group Vaccination"]]},
        fields=["parent", "parenttype"]
    )

    group_treatments = []
    group_vaccinations = []
    if participated_events:
        group_treatment_names = [
            d.parent for d in participated_events if d.parenttype == 'Group Treatment']
        group_vaccination_names = [
            d.parent for d in participated_events if d.parenttype == 'Group Vaccination']

        if group_treatment_names:
            group_treatments = frappe.get_all(
                "Group Treatment",
                filters={"name": ["in", group_treatment_names],
                         "docstatus": ["!=", 2]},
                fields=["name as record", "date",
                        "disease as details", "status"]
            )
            for gt in group_treatments:
                gt["event_type"] = "Group Treatment"
                gt["record_type"] = "Group Treatment"

        if group_vaccination_names:
            group_vaccinations = frappe.get_all(
                "Group Vaccination",
                filters={"name": ["in", group_vaccination_names],
                         "docstatus": ["!=", 2]},
                fields=["name as record", "date",
                        "vaccine as details", "status"]
            )
            for gv in group_vaccinations:
                gv["event_type"] = "Group Vaccination"
                gv["record_type"] = "Group Vaccination"

    # --- Step 3: Combine and Sort All Records ---
    combined_history = treatments + vaccinations + \
        group_treatments + group_vaccinations
    if not combined_history:
        return []
    return sorted(combined_history, key=lambda x: getdate(x.get("date")), reverse=True)


@frappe.whitelist()
def get_animals_in_group(group_name):
    """
    A reusable API function that fetches the animal list for a given Livestock Group.
    Args:
        group_name (str): The name of the Livestock Group document.
    Returns:
        list: A list of dictionaries, where each dictionary represents an animal in the group.
    """
    if not group_name:
        return []

    # Fetch the child table 'animal_list' from the specified Livestock Group
    group_animals = frappe.get_all(
        "Animal List",
        filters={"parent": group_name, "parenttype": "Livestock Group"},
        fields=["animal", "animal_name", "age"]
    )

    return group_animals


@frappe.whitelist()
def create_offspring_from_breeding_record(parent_data):
    """
    Creates a new Animal document from data passed from the client-side dialog.
    """
    try:
        # --- THE DEFINITIVE FIX ---
        # 2. Check if the incoming data is a string. If so, parse it from JSON into a Python dictionary.
        if isinstance(parent_data, str):
            parent_data = json.loads(parent_data)
        # --- END OF FIX ---

        new_animal = frappe.get_doc({
            "doctype": "Animal",
            # Now parent_data is guaranteed to be a dictionary, so .get() will work.
            "animal_id_tag_id": parent_data.get("animal_id_tag_id"),
            "gender": parent_data.get("gender"),
            "date_of_birth": parent_data.get("date_of_birth"),
            "acquisition_type": "Birth",
            "dam_mother": parent_data.get("dam_mother"),
            "sire_father": parent_data.get("sire_father"),
            "species": parent_data.get("species"),
            "breed": parent_data.get("breed"),
            "location_pen": parent_data.get("location_pen"),
            "status": "Active"  # Assuming 'Active' is a valid default for new births
        })
        new_animal.insert(ignore_permissions=True)
        return new_animal.name
    except Exception as e:
        frappe.log_error(frappe.get_traceback(), "Offspring Creation Failed")
        # This will now show the real error (e.g., a missing mandatory field)
        frappe.throw(f"Failed to create offspring. Server error: {e}")


@frappe.whitelist()
def get_breeding_history_for_animal(animal_id):
    """
    Fetches all breeding events where the animal is either the Dam or the Sire.
    This definitive version uses a direct SQL query for 100% accuracy.
    """
    if not animal_id:
        return []

    # --- THIS IS THE DEFINITIVE FIX ---
    # We use a direct SQL query to ensure the OR condition is handled correctly.
    events = frappe.db.sql("""
        SELECT
            name, 
            dam, 
            sire, 
            breeding_date, 
            expected_due_date, 
            outcome, 
            offspring, 
            birth_date
        FROM
            `tabBreeding Event`
        WHERE
            docstatus != 2 AND (dam = %(animal_id)s OR sire = %(animal_id)s)
        ORDER BY
            breeding_date DESC
    """, {"animal_id": animal_id}, as_dict=1)
    # --- END OF FIX ---

    # The rest of the logic remains the same.
    # We determine the 'mate' for each event relative to the current animal.
    for event in events:
        if event.get("dam") == animal_id:
            event["mate"] = event.get("sire")
        else:
            event["mate"] = event.get("dam")

    return events


@frappe.whitelist()
def get_human_readable_age(birth_date_str):
    """
    Calculates the age in a "years, months, days" format from a date string.
    This is the robust, server-side method.
    """
    if not birth_date_str:
        return "Set Date of Birth"

    try:
        today = getdate(nowdate())
        birth_date = getdate(birth_date_str)

        # relativedelta is a powerful tool that handles all edge cases like leap years.
        delta = relativedelta(today, birth_date)

        parts = []
        if delta.years > 0:
            parts.append(f"{delta.years} year{'s' if delta.years > 1 else ''}")
        if delta.months > 0:
            parts.append(
                f"{delta.months} month{'s' if delta.months > 1 else ''}")
        if delta.days > 0:
            parts.append(f"{delta.days} day{'s' if delta.days > 1 else ''}")

        if not parts:
            return "Newborn"

        return ", ".join(parts)

    except Exception:
        # Failsafe in case of an invalid date format
        return "Invalid Date"


@frappe.whitelist()
def create_serial_no_for_animal(animal_doc_name):
    """
    Creates a Serial No document for an Animal.
    NOTE: This only creates the Serial No record; it does not set its location.
    The location must be set via a Stock Entry or Purchase Receipt.
    """
    animal = frappe.get_doc("Animal", animal_doc_name)

    if not animal.item_code:
        frappe.throw("Please set the 'Item Code' before creating a Serial No.")

    serial_no_name = animal.animal_id_tag_id

    if frappe.db.exists("Serial No", serial_no_name):
        return serial_no_name

    try:
        sn = frappe.new_doc("Serial No")
        sn.serial_no = serial_no_name
        sn.item_code = animal.item_code

        # --- THIS IS THE CRITICAL FIX ---
        # We DO NOT set the warehouse here. This is forbidden by ERPNext.
        # sn.warehouse = animal.location_pen
        # --- END OF FIX ---

        sn.insert(ignore_permissions=True)
        return sn.name

    except Exception as e:
        frappe.log_error(frappe.get_traceback())
        frappe.throw(f"Failed to create Serial No. Server error: {e}")


@frappe.whitelist()
def create_and_submit_stock_receipt(animal_doc_name):
    """
    Creates AND submits a Material Receipt Stock Entry for a given Animal.
    This is a complete, one-step server-side function.
    Returns the name of the submitted Stock Entry.
    """
    animal = frappe.get_doc("Animal", animal_doc_name)

    # --- Validation ---
    if not animal.item_code or not animal.location_pen or not animal.serial_no:
        frappe.throw(
            "Animal must have an Item Code, Location, and Serial No before it can be received into stock.")

    if frappe.db.get_value("Serial No", animal.serial_no, "warehouse"):
        frappe.throw(
            f"This animal's Serial No ({animal.serial_no}) is already in stock.")

    try:
        # --- Create the Stock Entry in memory ---
        se = frappe.new_doc("Stock Entry")
        se.stock_entry_type = "Material Receipt"
        se.purpose = "Material Receipt"  # Also set purpose for clarity
        se.set_posting_time = 1
        se.posting_date = nowdate()
        se.posting_time = frappe.utils.nowtime()

        # Append the item to the child table
        se.append("items", {
            "item_code": animal.item_code,
            "t_warehouse": animal.location_pen,
            "qty": 1,
            "serial_no": animal.serial_no
            # Add basic_rate here if you have a purchase value on the animal
        })

        # --- Insert and Submit the Document ---
        se.insert(ignore_permissions=True)
        se.submit()

        frappe.msgprint(
            f"Stock Entry {se.name} created and submitted successfully.")
        return se.name

    except Exception as e:
        frappe.log_error(frappe.get_traceback())
        frappe.throw(f"Failed to create Stock Entry. Server error: {e}")


@frappe.whitelist()
def get_group_health_history(livestock_group):
    """Fetches Group Treatment records for a specific Livestock Group."""
    return frappe.get_all(
        "Group Treatment",
        filters={"livestock_group": livestock_group, "docstatus": 1},
        fields=["name", "date", "disease", "total_cost"],
        order_by="date desc"
    )


@frappe.whitelist()
def get_group_feeding_history(poultry_flock_id):
    """
    Fetches a correctly categorized history of all feeding events.
    It correctly distinguishes between Direct and Scheduled feedings.
    """
    if not poultry_flock_id:
        return []

    flock_data = frappe.db.get_value("Poultry Flock", poultry_flock_id, [
                                     "livestock_group", "item"], as_dict=True)
    if not flock_data or not flock_data.livestock_group:
        return []

    livestock_group = flock_data.livestock_group
    flock_item_code = flock_data.item

    final_history = []
    processed_schedules = set()

    # Step 1: Get ALL submitted Stock Entries that are feedings for this group.
    stock_entries = frappe.db.sql("""
        SELECT
            se.name as record,
            se.posting_date as date,
            sed.item_code as item,
            sed.qty,
            se.custom_feeding_schedule
        FROM `tabStock Entry` as se
        JOIN `tabStock Entry Detail` as sed ON se.name = sed.parent
        WHERE
            se.custom_livestock_group = %(livestock_group)s
            AND se.docstatus = 1
            AND se.purpose = 'Material Issue'
            AND sed.item_code != %(flock_item_code)s
    """, {"livestock_group": livestock_group, "flock_item_code": flock_item_code}, as_dict=1)

    # Step 2: Correctly categorize each Stock Entry.
    for se in stock_entries:
        if se.custom_feeding_schedule:
            se['type'] = 'Completed Scheduled Feeding'
            processed_schedules.add(se.custom_feeding_schedule)
        else:
            # This is the key logic that was broken.
            se['type'] = 'Direct Feeding'

        se['record_type'] = 'Stock Entry'
        final_history.append(se)

    # Step 3: Get all submitted Feeding Schedules and add ONLY the ones that have NOT been processed.
    all_schedules = frappe.get_all("Feeding Schedule",
                                   filters={
                                       "livestock_group": livestock_group, "docstatus": 1},
                                   fields=["name as record", "date", "feed_formulation as item", "quantity_to_feed as qty"])

    for s in all_schedules:
        if s.record not in processed_schedules:
            s["type"] = "Planned Feeding"
            s["record_type"] = "Feeding Schedule"
            final_history.append(s)

    if not final_history:
        return []

    return sorted(final_history, key=lambda x: getdate(x.get("date")), reverse=True)


@frappe.whitelist()
def get_flock_health_history(poultry_flock_id):
    """
    Fetches a combined and sorted history of health events (vaccinations, treatments).
    """
    livestock_group = frappe.db.get_value(
        "Poultry Flock", poultry_flock_id, "livestock_group")
    if not livestock_group:
        return []

    vaccinations = frappe.get_all("Group Vaccination", filters={"livestock_group": livestock_group, "docstatus": 1},
                                  fields=["name", "date", "vaccine", "status"])
    health_history = []
    for v in vaccinations:
        health_history.append({"date": v.date, "event_type": "Vaccination",
                               "details": f"Vaccinated with: {v.vaccine}", "status": v.status,
                               "record_type": "Group Vaccination", "record": v.name})

    treatments = frappe.get_all("Group Treatment", filters={"livestock_group": livestock_group, "docstatus": 1},
                                fields=["name", "date", "disease", "status"])
    for t in treatments:
        health_history.append({"date": t.date, "event_type": "Treatment",
                               "details": f"Treated for: {t.disease or 'Unspecified'}", "status": t.status,
                               "record_type": "Group Treatment", "record": t.name})

    return sorted(health_history, key=lambda x: getdate(x.get("date")), reverse=True)


@frappe.whitelist()
def get_flock_financials(poultry_flock_id):
    """
    Calculates total costs for feed and health for a given flock.
    """
    flock_data = frappe.db.get_value("Poultry Flock", poultry_flock_id, [
                                     "livestock_group", "item"], as_dict=True)
    if not flock_data or not flock_data.livestock_group:
        return {}

    livestock_group = flock_data.livestock_group
    flock_item_code = flock_data.item

    # Calculate total health costs
    health_costs = frappe.db.sql("""
        SELECT SUM(total_cost) FROM `tabGroup Vaccination` WHERE livestock_group=%s AND docstatus=1
        UNION ALL
        SELECT SUM(total_cost) FROM `tabGroup Treatment` WHERE livestock_group=%s AND docstatus=1
    """, (livestock_group, livestock_group))
    total_health_cost = sum(flt(row[0]) for row in health_costs if row[0])

    # Calculate total feed costs, excluding mortality write-offs
    feed_cost_data = frappe.db.sql("""
        SELECT SUM(sed.basic_amount)
        FROM `tabStock Entry Detail` sed
        JOIN `tabStock Entry` se ON sed.parent = se.name
        WHERE se.custom_livestock_group = %s AND se.docstatus = 1 AND sed.item_code != %s
    """, (livestock_group, flock_item_code))
    total_feed_cost = flt(
        feed_cost_data[0][0]) if feed_cost_data and feed_cost_data[0][0] else 0

    return {
        "total_medication_cost": total_health_cost,
        "total_feed_cost": total_feed_cost
    }


@frappe.whitelist()
def get_flock_mortality_history(poultry_flock_id):
    """
    Fetches a history of mortality events (Stock Entries) for a given flock.
    """
    flock_data = frappe.db.get_value("Poultry Flock", poultry_flock_id, [
                                     "livestock_group", "item"], as_dict=True)
    if not flock_data or not flock_data.livestock_group:
        return []

    livestock_group = flock_data.livestock_group
    flock_item_code = flock_data.item

    # Query for "Material Issue" stock entries where the item is the flock itself.
    mortality_entries = frappe.db.sql("""
        SELECT
            se.posting_date as date,
            sed.qty as quantity,
            se.remarks as cause,
            se.name as record
        FROM
            `tabStock Entry` as se
        JOIN
            `tabStock Entry Detail` as sed ON se.name = sed.parent
        WHERE
            se.custom_livestock_group = %(livestock_group)s
            AND se.docstatus = 1
            AND se.purpose = 'Material Issue'
            AND sed.item_code = %(flock_item_code)s
        ORDER BY
            se.posting_date DESC
    """, {
        "livestock_group": livestock_group,
        "flock_item_code": flock_item_code
    }, as_dict=1)

    for entry in mortality_entries:
        entry["record_type"] = "Stock Entry"

    return mortality_entries


@frappe.whitelist()
def get_flock_sales_history(poultry_flock_id):
    """
    Fetches a history of sales (Delivery Notes) for a given flock.
    """
    livestock_group = frappe.db.get_value(
        "Poultry Flock", poultry_flock_id, "livestock_group")
    if not livestock_group:
        return []

    # --- THIS QUERY IS NOW CORRECT ---
    # It now queries the parent Delivery Note document for the custom link.
    sales_entries = frappe.db.sql("""
        SELECT
            dn.posting_date as date,
            dn.customer as customer,
            dn.total_qty as quantity,
            dn.base_grand_total / dn.total_qty as rate,
            dn.base_grand_total as total_amount,
            dn.name as record
        FROM
            `tabDelivery Note` as dn
        WHERE
            dn.custom_livestock_group = %(livestock_group)s
            AND dn.docstatus = 1
        ORDER BY
            dn.posting_date DESC
    """, {
        "livestock_group": livestock_group
    }, as_dict=1)
    # --- END OF FIX ---

    for entry in sales_entries:
        entry["record_type"] = "Delivery Note"

    return sales_entries


@frappe.whitelist()
def get_total_daily_egg_production():
    """
    A standalone API function for a dashboard chart.
    It calculates the SUM of all eggs collected from ALL flocks, grouped by day.
    """
    # This query finds all submitted "Egg Collection" logs,
    # groups them by date, and sums the quantity for each date.
    all_egg_logs = frappe.db.sql("""
        SELECT
            date,
            SUM(quantity) as total_quantity
        FROM
            `tabLivestock Performance Log`
        WHERE
            log_type = 'Egg Collection'
            AND docstatus = 1
        GROUP BY
            date
        ORDER BY
            date ASC
    """, as_dict=1)

    # Frappe Charts expects the data in this exact format
    labels = []
    values = []
    for row in all_egg_logs:
        labels.append(row.date)
        values.append(row.total_quantity)

    if not labels:
        return {}  # Return an empty object if there's no data

    return {
        "labels": labels,
        "datasets": [
            {
                "name": "Total Eggs Collected Per Day",
                "values": values
            }
        ]
    }


@frappe.whitelist()
def get_flock_stock_dashboard_data(item_code, batch_no):
    """
    A custom data source for the Item Dashboard component.
    This function fetches stock levels ONLY for a specific batch,
    ignoring all other stock for the same item.
    """
    if not item_code or not batch_no:
        return []
    # The Bin table holds the real-time stock level for a specific item
    # in a specific warehouse, and optionally for a specific batch.
    # This is the most efficient way to get the current stock.
    stock_data = frappe.get_all(
        "Bin",
        filters={
            "item_code": item_code,
            "batch_no": batch_no
        },
        fields=["warehouse", "actual_qty", "valuation_rate"]
    )

    # The dashboard component expects the data in this list-of-dictionaries format.
    return stock_data


@frappe.whitelist()
def get_flock_stock_dashboard_data(item_code, batch_no, warehouse):
    """
    A custom data source for the Item Dashboard that is compatible with older ERPNext versions.
    It gets the precise batch quantity from the Stock Ledger and other metrics from the Bin.
    """
    if not all([item_code, batch_no, warehouse]):
        return []

    # 1. Get the definitive, real-time quantity for the specific batch from the Stock Ledger.
    ledger_data = frappe.db.sql("""
        SELECT SUM(actual_qty)
        FROM `tabStock Ledger Entry`
        WHERE item_code = %(item_code)s AND warehouse = %(warehouse)s AND batch_no = %(batch_no)s
    """, {"item_code": item_code, "warehouse": warehouse, "batch_no": batch_no})

    actual_batch_qty = flt(
        ledger_data[0][0]) if ledger_data and ledger_data[0][0] else 0

    # 2. Get the general reservation/projection data from the Bin for that item/warehouse.
    # In this ERPNext version, these are not batch-specific.
    bin_data = frappe.get_all("Bin",
                              filters={"item_code": item_code,
                                       "warehouse": warehouse},
                              fields=["projected_qty", "reserved_qty", "reserved_qty_for_production",
                                      "reserved_qty_for_sub_contract", "valuation_rate"]
                              )

    # If there's no stock record at all, there's nothing to show.
    if not bin_data and actual_batch_qty == 0:
        return []

    # 3. Build the final data dictionary, combining the two sources.
    if bin_data:
        result = bin_data[0]
    else:  # Create a default dict if no Bin exists yet but there is ledger stock
        result = frappe._dict({})

    # Overwrite the generic Bin quantity with our precise batch quantity.
    result['actual_qty'] = actual_batch_qty
    result['item_code'] = item_code
    result['warehouse'] = warehouse

    # 4. Enrich the data with the same logic as the standard dashboard to satisfy the template.
    item_details = frappe.get_cached_value(
        "Item", item_code, ["item_name", "stock_uom", "has_batch_no", "has_serial_no"])

    total_reserved = (
        flt(result.get("reserved_qty")) + flt(result.get("reserved_qty_for_production")
                                              ) + flt(result.get("reserved_qty_for_sub_contract"))
    )

    actual_or_pending = flt(result.get("projected_qty")) + total_reserved
    pending_qty = max(0, actual_or_pending - actual_batch_qty)

    result.update({
        "item_name": item_details[0],
        "stock_uom": item_details[1],
        "disable_quick_entry": item_details[2] or item_details[3],
        "total_reserved": total_reserved,
        "pending_qty": pending_qty
    })

    return [result]


@frappe.whitelist()
def get_planned_feeding_for_date(schedule_name, target_date):
    """
        Fetches a single 'Planned' row from a Feeding Schedule for a specific date.
        """
    log_row = frappe.db.get_value("Feeding Schedule Log", {
        "parent": schedule_name,
        "date": target_date,
        "status": "Planned"
    }, ["name", "recommended_quantity"], as_dict=True)

    return log_row


@frappe.whitelist()
def get_animal_feeding_history(animal_id):
    """
    Fetches the feeding history for a single animal from its child table.
    """
    if not animal_id:
        return []

    # The child table is the direct source of truth for the animal's history
    feeding_log = frappe.get_all("Animal Feeding Log",
                                 filters={"parent": animal_id,
                                          "parenttype": "Animal"},
                                 fields=["date", "description", "quantity_consumed_est",
                                         "source_doctype", "source_document"],
                                 order_by="date desc"
                                 )
    return feeding_log
