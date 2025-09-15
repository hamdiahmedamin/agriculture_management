# Copyright (c) 2025, aminos and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import getdate
import re


class HarvestEntry(Document):
    # This hook is the heart of the new logic. It runs automatically when the user clicks "Submit".
    def on_submit(self):
        self.validate_submission()
        self.process_harvest_rows()
        # Set final status in memory before saving
        self.set_status("Completed")

    # This hook runs when a Submitted document is "Cancelled".
    def on_cancel(self):
        self.reverse_stock_entries_and_delete_logs()
        # Set final status in memory before saving
        self.set_status("Cancelled")

    def validate_submission(self):
        """Perform checks before processing."""
        if not self.zones_harvested:
            frappe.throw(
                _("Please add at least one zone to the harvest list before submitting."))
        if not self.item_code or not self.target_warehouse:
            frappe.throw(
                _("Please select the 'Item' and 'Target Warehouse' before submitting."))

    def process_harvest_rows(self):
        """Loop through child table, create Stock Entries and Harvest Logs."""
        for row in self.get("zones_harvested"):
            # Create Stock Entry to update inventory
            stock_entry = self.create_stock_entry_for_zone(row)
            stock_entry.submit()

            # Create the detailed Harvest Log for agricultural records
            new_log = self.create_harvest_log_for_zone(row, stock_entry.name)
            new_log.submit()

            # Link the generated log back to the child table row in memory
            row.generated_harvest_log = new_log.name

    def create_stock_entry_for_zone(self, zone_row):
        """Creates, saves, and returns a 'Material Receipt' Stock Entry document."""
        stock_entry = frappe.get_doc({
            "doctype": "Stock Entry",
            "stock_entry_type": "Material Receipt",
            "company": self.company,
            "to_warehouse": self.target_warehouse,
            "items": [{
                "item_code": self.item_code,
                "qty": zone_row.quantity_harvested,
                "uom": zone_row.uom,
                "t_warehouse": self.target_warehouse,
            }],
            # You should add a custom field 'source_harvest_entry' to Stock Entry
            "source_harvest_entry": self.name
        })
        stock_entry.insert(ignore_permissions=True)
        return stock_entry

    def create_harvest_log_for_zone(self, zone_row, stock_entry_name):
        """Creates, saves, and returns a detailed Harvest Log document."""
        harvest_date_str = getdate(self.harvest_date).strftime('%Y-%m-%d')
        title = f"Harvest - {zone_row.growing_zone} on {harvest_date_str}"

        new_log = frappe.get_doc({
            "doctype": "Harvest Log",
            "title": title,
            "total_weight_gross": zone_row.quantity_harvested,
            "crop_cycle": self.crop_cycle,
            "harvested_by": self.harvested_by,
            "harvest_date": self.harvest_date,
            "growing_zone": zone_row.growing_zone,
            "weight_uom": zone_row.uom,
            "quality_grade": zone_row.quality_grade,
            "waste_weight": zone_row.waste_weight,

            # THIS IS THE CORRECTED LINE:
            "harvest_notes": zone_row.notes,

            "source_harvest_entry": self.name,
            "linked_stock_entry": stock_entry_name
        })

        new_log.append("harvested_items", {
            "item_code": self.item_code,
            "target_warehouse": self.target_warehouse,
            "quantity": zone_row.quantity_harvested,
            "uom": zone_row.uom,
            "quality_grade": zone_row.quality_grade,
            "harvest_date": self.harvest_date
        })

        new_log.insert(ignore_permissions=True)
        return new_log

    def reverse_stock_entries_and_delete_logs(self):
        """On cancellation, cancel linked Stock Entries and delete Harvest Logs."""
        for row in self.get("zones_harvested"):
            if row.generated_harvest_log:
                try:
                    log_doc = frappe.get_doc(
                        "Harvest Log", row.generated_harvest_log)

                    if getattr(log_doc, "linked_stock_entry", None):
                        se = frappe.get_doc(
                            "Stock Entry", log_doc.linked_stock_entry)
                        if se.docstatus == 1:
                            se.cancel()

                    frappe.delete_doc(
                        "Harvest Log", log_doc.name, ignore_permissions=True)
                except frappe.DoesNotExistError:
                    pass

    # This is a helper function to avoid repeating the self.db_set line
    def set_status(self, status):
        self.status = status
        frappe.db.set_value(self.doctype, self.name,
                            "status", status, update_modified=False)


@frappe.whitelist()
def get_system_layout_details(crop_cycle):
    """
    Fetches the layout details by reading individual custom fields
    from the Asset linked to the given Crop Cycle.
    """
    if not crop_cycle:
        return None

    # Find the Asset (Hydroponic System) linked to the Crop Cycle
    hydroponic_system = frappe.get_value(
        "Crop Cycle", crop_cycle, "hydroponic_system")
    if not hydroponic_system:
        frappe.throw(
            _("The selected Crop Cycle is not linked to a Hydroponic System (Asset)."))

    # Fetch the layout details from the Asset document using your specific field names
    asset_details = frappe.get_doc("Asset", hydroponic_system)

    # Get the values from your custom fields
    racks = asset_details.get("custom_number_of_racks")
    tiers = asset_details.get("custom_tiers_per_rack")
    gullies = asset_details.get("custom_gullies_per_tier")
    prefix = asset_details.get("custom_naming_prefix")

    # Validate that the necessary fields have values
    if not all([racks, tiers, gullies]):
        frappe.throw(
            _("The linked Hydroponic System '{0}' is missing one or more layout values (Racks, Tiers, or Gullies).").format(
                hydroponic_system)
        )

    # Construct the JSON object that the client-side script expects
    layout = {
        "racks": int(racks),
        "tiers": int(tiers),
        "gullies": int(gullies),
        "prefix": prefix or "Rack"  # Use 'Rack' as a default if the prefix is not set
    }

    return layout


@frappe.whitelist()
def get_zones_by_structure(crop_cycle, rack_num, tier_num, gully_start, gully_end, existing_zones):
    """
    Parses zone names to find all zones within a specific rack, tier, and gully range.
    This version uses a more flexible regex that only looks for numbers in order.
    """
    if not all([crop_cycle, rack_num, tier_num, gully_start, gully_end]):
        return []

    # Get all zones linked to the crop cycle
    all_zones_in_cycle_docs = frappe.get_all(
        "Crop Cycle Zone", filters={"parent": crop_cycle}, fields=["growing_zone"])
    all_zone_names = {d.growing_zone for d in all_zones_in_cycle_docs}

    # Remove zones that are already in the table
    if isinstance(existing_zones, str):
        import json
        existing_zones = json.loads(existing_zones)
    available_zones = all_zone_names - set(existing_zones)

    matching_zones = []

    # --- THIS IS THE ENHANCED REGEX ---
    # It finds the first three numbers in the string, assuming they are Rack, Tier, and Gully in order.
    # This is much more flexible than looking for specific letters like R, T, G.
    pattern = re.compile(r"(\d+).*?(\d+).*?(\d+)")
    # --- END OF ENHANCEMENT ---

    for zone_name in available_zones:
        # We search from the end of the string to better handle prefixes like "GZ-2025-"
        match = pattern.search(zone_name)
        if match and len(match.groups()) == 3:
            try:
                r, t, g = [int(num) for num in match.groups()]
                if (r == int(rack_num) and
                    t == int(tier_num) and
                        int(gully_start) <= g <= int(gully_end)):
                    matching_zones.append(zone_name)
            except (ValueError, TypeError):
                continue

    return sorted(matching_zones)
