# Copyright (c) 2025, aminos and contributors
# For license information, please see license.txt

# livestock_movement.py
import frappe
from frappe.model.document import Document


class LivestockMovement(Document):
    def validate(self):
        # This logic is already correct and fetches the 'from_location'
        if self.movement_type == "Individual" and self.animal:
            self.from_location = frappe.db.get_value(
                "Animal", self.animal, "location_pen")
        elif self.movement_type == "Group" and self.livestock_group:
            self.from_location = frappe.db.get_value(
                "Livestock Group", self.livestock_group, "group_location")

        if self.from_location == self.to_location:
            frappe.throw(
                "The 'From Location' and 'To Location' cannot be the same.")

    def on_submit(self):
        """
        On submit, update the location for either the single animal or the group and all its members.
        """
        if self.movement_type == "Individual":
            self.update_animal_location(self.animal, self.to_location)
            frappe.msgprint(
                f"Animal {self.animal} moved to {self.to_location}.")

        elif self.movement_type == "Group":
            # --- THIS IS THE CRITICAL FIX ---
            # Step 1: Update the parent Livestock Group's location first.
            frappe.db.set_value(
                "Livestock Group", self.livestock_group, "group_location", self.to_location)
            # --- END OF FIX ---

            # Step 2: Get all animals in the group.
            animals_in_group = frappe.get_all(
                "Animal List",
                filters={"parent": self.livestock_group,
                         "parenttype": "Livestock Group"},
                pluck="animal"
            )

            # Step 3: Loop through each animal and update its location.
            for animal_id in animals_in_group:
                self.update_animal_location(animal_id, self.to_location)

            frappe.msgprint(
                f"Group {self.livestock_group} and all its {len(animals_in_group)} animals moved to {self.to_location}.")

    def on_cancel(self):
        """
        On cancel, revert the location for either the single animal or the group and all its members.
        """
        if self.movement_type == "Individual":
            self.update_animal_location(self.animal, self.from_location)
            frappe.msgprint(
                f"Movement cancelled. Animal {self.animal} reverted to {self.from_location}.")

        elif self.movement_type == "Group":
            # --- THIS IS THE CRITICAL FIX ---
            # Step 1: Revert the parent Livestock Group's location.
            frappe.db.set_value(
                "Livestock Group", self.livestock_group, "group_location", self.from_location)
            # --- END OF FIX ---

            animals_in_group = frappe.get_all(
                "Animal List",
                filters={"parent": self.livestock_group,
                         "parenttype": "Livestock Group"},
                pluck="animal"
            )

            # Step 2: Revert each animal's location.
            for animal_id in animals_in_group:
                self.update_animal_location(animal_id, self.from_location)

            frappe.msgprint(
                f"Movement cancelled. Group {self.livestock_group} reverted to {self.from_location}.")

    def update_animal_location(self, animal_id, new_location):
        """Helper function to update a single animal's location."""
        try:
            frappe.db.set_value("Animal", animal_id,
                                "location_pen", new_location)
        except Exception as e:
            frappe.log_error(
                f"Failed to update location for Animal {animal_id}: {e}")
