# Copyright (c) 2025, aminos and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.utils import getdate


class PlantingSchedule(Document):
    # We are moving all logic from validate() to before_save()
    # The validate() hook can be removed or left empty.

    def before_save(self):
        """
        This hook runs before saving but AFTER the document object is fully
        populated with data from the form, including child tables.
        This is the reliable place for our validations.
        """
        self.validate_required_fields()
        self.validate_dates()
        self.validate_zone_availability()

    def validate_required_fields(self):
        """

        Ensures that a location or system is selected based on the schedule type.
        """
        if self.is_hydroponic_schedule:
            if not self.hydroponic_system:
                frappe.throw(
                    "For a Hydroponic Schedule, you must select a <b>Hydroponic System</b>.")

            # This check will now work correctly because self.growing_zones is populated.
            if not self.growing_zones:
                frappe.throw(
                    "You must select at least one <b>Growing Zone</b> for the schedule.")
        else:
            if not self.location:
                frappe.throw(
                    "For a standard schedule, you must select a <b>Location</b>.")

    def validate_dates(self):
        """Ensures that the estimated harvest date is after the planting date."""
        if self.estimated_harvest_date and self.target_planting_date:
            if getdate(self.estimated_harvest_date) <= getdate(self.target_planting_date):
                frappe.throw(
                    "<b>Estimated Harvest Date</b> must be after the <b>Target Planting Date</b>.")

    def validate_zone_availability(self):
        """
        Checks if any of the selected Growing Zones are already scheduled for another crop
        during the same overlapping period.
        """
        if not self.is_hydroponic_schedule or not self.growing_zones or not self.target_planting_date or not self.estimated_harvest_date:
            return

        zones_in_this_schedule = [
            zone.growing_zone for zone in self.growing_zones]

        overlapping_schedules = frappe.db.sql("""
            SELECT
                parent.name,
                child.growing_zone
            FROM
                `tabPlanting Schedule Zone` AS child
            JOIN
                `tabPlanting Schedule` AS parent ON child.parent = parent.name
            WHERE
                parent.name != %(current_schedule)s
                AND parent.status != 'Cancelled'
                AND parent.is_hydroponic_schedule = 1
                AND child.growing_zone IN %(zones)s
                AND parent.target_planting_date <= %(end_date)s
                AND parent.estimated_harvest_date >= %(start_date)s
        """, {
            "current_schedule": self.name or "New Planting Schedule",  # Handle new doc case
            "zones": zones_in_this_schedule,
            "start_date": self.target_planting_date,
            "end_date": self.estimated_harvest_date
        }, as_dict=True)

        if overlapping_schedules:
            error_details = ", ".join(
                [f"{s.growing_zone} in schedule {s.name}" for s in overlapping_schedules])
            frappe.throw(
                f"The following Growing Zones are already booked for this period: <b>{error_details}</b>"
            )
