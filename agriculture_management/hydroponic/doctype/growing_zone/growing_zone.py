# Copyright (c) 2025, aminos and contributors
# For license information, please see license.txt

# Copyright (c) 2025, aminos and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.utils import nowdate, date_diff
from frappe import _


class GrowingZone(Document):
    def before_save(self):
        """
        Main function to update all calculated fields before the document is saved.
        """
        if self.current_crop_cycle:
            self.update_details_from_crop_cycle()
        else:
            self.clear_crop_cycle_details()

    def update_details_from_crop_cycle(self):
        """
        Fetches data from the linked Crop Cycle and populates the Growing Zone fields.
        """
        try:
            crop_cycle_doc = frappe.get_doc(
                "Crop Cycle", self.current_crop_cycle)

            # Fetch basic details
            self.current_crop = crop_cycle_doc.crop
            self.date_planted = crop_cycle_doc.start_date
            self.expected_harvest_date = crop_cycle_doc.expected_harvest_date

            # Calculate days in cycle
            if self.date_planted:
                self.days_in_cycle = date_diff(nowdate(), self.date_planted)
            else:
                self.days_in_cycle = 0

            # Calculate occupancy
            if self.plant_capacity and crop_cycle_doc.total_plants:
                self.occupancy = (float(crop_cycle_doc.total_plants) /
                                  float(self.plant_capacity)) * 100
            else:
                self.occupancy = 0

            self.update_last_harvest_info()

        except frappe.DoesNotExistError:
            frappe.msgprint(f"Crop Cycle {self.current_crop_cycle} not found.")
            self.clear_crop_cycle_details()

    def clear_crop_cycle_details(self):
        """
        Clears all crop-related fields if no crop cycle is linked.
        """
        self.current_crop = None
        self.date_planted = None
        self.expected_harvest_date = None
        self.days_in_cycle = 0
        self.occupancy = 0

    def update_last_harvest_info(self):
        """
        Finds the most recent completed 'Harvest Entry' for this growing zone.
        This version uses the correct child table filter syntax for older Frappe versions.
        """
        # Query the PARENT table ('Harvest Entry')
        last_harvest_details = frappe.get_all(
            "Harvest Entry",
            # THIS IS THE CORRECTED FILTER SYNTAX:
            filters=[
                ["Harvest Entry Zone", "growing_zone", "=", self.name],
                ["Harvest Entry", "status", "=", "Completed"],
            ],
            fields=[
                "name",  # Fetch the name of the Harvest Entry parent doc
                "harvest_date"
            ],
            order_by="harvest_date desc",  # Sort by the date in the parent doc
            limit=1
        )

        if last_harvest_details:
            latest_entry_parent = last_harvest_details[0]

            # Now get the specific quantity from the child table row.
            # This part remains the same as it was already correct.
            child_row = frappe.get_all(
                "Harvest Entry Zone",
                filters={
                    "parent": latest_entry_parent.name,
                    "growing_zone": self.name
                },
                fields=["quantity_harvested"],
                limit=1
            )

            # Set the values
            self.last_harvest_date = latest_entry_parent.harvest_date
            self.last_yield = child_row[0].quantity_harvested if child_row else 0
        else:
            # If no harvest has ever been logged, clear the fields
            self.last_harvest_date = None
            self.last_yield = 0

    def on_trash(self):
        """
        Prevents deletion of a Growing Zone if it has an active crop cycle.
        This hook is called when a user tries to delete the document.
        """
        if self.current_crop_cycle:
            frappe.throw(
                title="Deletion Prohibited",
                msg=_(
                    "Cannot delete Growing Zone <strong>{0}</strong> because it is linked to an active Crop Cycle ({1}). Please remove the link from the Crop Cycle before deleting this zone."
                ).format(self.zone_name, self.current_crop_cycle)
            )

    def before_delete(self):
        """
        This hook is called before a document is permanently deleted from the trash.
        """
        self.on_trash()


@frappe.whitelist()
def get_latest_environmental_reading(zone_name):
    """
    Finds the latest 'Water Quality Reading' for a given Growing Zone
    by tracing it back through its parent Asset to its Water Reservoir.
    """
    try:
        # Step 1: Get the parent Hydroponic System (Asset) from the Growing Zone
        parent_asset = frappe.get_value(
            "Growing Zone", zone_name, "hydroponic_system")
        if not parent_asset:
            return None

        # Step 2: Get the Water Reservoir linked to that Asset
        # IMPORTANT: This assumes your 'Asset' DocType has a field named 'water_reservoir'
        # that links to the Water Reservoir. If your field is named differently, change it here.
        water_reservoir = frappe.get_value(
            "Asset", parent_asset, "custom_water_reservoir")
        if not water_reservoir:
            return None

        # Step 3: Find the most recent 'Water Quality Reading' for that reservoir
        latest_reading = frappe.get_all(
            "Water Quality Reading",
            filters={"water_reservoir": water_reservoir, "docstatus": 1},
            fields=["ph", "electrical_conductivity",
                    "water_temperature", "modified"],
            order_by="modified desc",
            limit=1
        )

        return latest_reading[0] if latest_reading else None

    except Exception as e:
        frappe.log_error(
            f"Error fetching environmental reading for zone {zone_name}: {e}")
        return None
