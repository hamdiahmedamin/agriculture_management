# Copyright (c) 2025, aminos and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.utils import get_datetime


class WaterQualityLog(Document):
    def validate(self):
        """
        Server-side validation that runs before the document is saved.
        """
        self.validate_measurements()

    def validate_measurements(self):
        """
        Ensure that the measured values are within a reasonable range.
        """
        if self.measured_ph is not None and not (0 <= self.measured_ph <= 14):
            frappe.throw("<b>Measured pH</b> must be between 0 and 14.")

        if self.measured_ec_mscm is not None and self.measured_ec_mscm < 0:
            frappe.throw("<b>Measured EC</b> cannot be a negative value.")

        if self.reservoir_level_ is not None and not (0 <= self.reservoir_level_ <= 100):
            frappe.throw(
                "<b>Reservoir Level</b> must be a percentage between 0 and 100.")

# =====================================================================
# === WHITELISTED FUNCTION ===
# =====================================================================


@frappe.whitelist()
def get_targets_from_crop_cycle(crop_cycle_name):
    """
    Securely fetches the target pH and EC from the Nutrient Recipe
    linked to the given Crop Cycle.
    """
    if not crop_cycle_name:
        return None

    # Get the linked Nutrient Recipe from the Crop Cycle
    nutrient_recipe_name = frappe.db.get_value(
        "Crop Cycle", crop_cycle_name, "nutrient_recipe")

    if not nutrient_recipe_name:
        # If no recipe is linked, we can't provide targets.
        return {"target_ph": None, "target_ec": None}

    # Fetch the target values from the Nutrient Recipe document
    targets = frappe.db.get_value(
        "Nutrient Recipe",
        nutrient_recipe_name,
        ["target_ph", "target_ec"],
        as_dict=True
    )

    return targets
