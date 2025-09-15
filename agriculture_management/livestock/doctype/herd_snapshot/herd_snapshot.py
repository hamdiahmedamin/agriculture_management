# Copyright (c) 2025, aminos and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.utils import nowdate, flt


class HerdSnapshot(Document):
    def before_insert(self):
        """
        Automatically populates the snapshot with data from the source Livestock Group.
        """
        if not self.livestock_group:
            frappe.throw(
                "A source Livestock Group must be selected to create a snapshot.")

        # --- Step 1: Fetch the Source Group and its Animals ---
        source_group = frappe.get_doc("Livestock Group", self.livestock_group)

        if not source_group.animal_list:
            frappe.throw("Cannot create a snapshot for an empty group.")

        animal_names = [d.animal for d in source_group.animal_list]

        animal_data_map = {
            d.name: d for d in frappe.get_all(
                "Animal",
                filters={"name": ["in", animal_names]},
                fields=["name", "age", "current_weight", "asset"]
            )
        }

        # --- Step 2: Initialize variables for calculation ---
        total_age = 0.0
        total_weight = 0.0
        total_asset_value = 0.0
        animal_count = len(animal_names)

        # --- Step 3: Populate the Child Table and Calculate Totals ---
        for animal_row in source_group.animal_list:
            animal_doc_data = animal_data_map.get(animal_row.animal)
            if not animal_doc_data:
                continue

            asset_value = 0.0
            if animal_doc_data.asset:
                # --- THIS IS THE CORRECTED LINE ---
                # The correct field name for an asset's value is 'gross_purchase_amount'.
                asset_value = frappe.db.get_value(
                    "Asset", animal_doc_data.asset, "gross_purchase_amount") or 0.0
                # --- END OF FIX ---

            self.append("snapshot_animal_list", {
                "animal": animal_doc_data.name,
                "age_at_snapshot": animal_doc_data.age,
                "weight_at_snapshot": animal_doc_data.current_weight,
                "asset_value_at_snapshot": asset_value
            })

            total_age += flt(animal_doc_data.age)
            total_weight += flt(animal_doc_data.current_weight)
            total_asset_value += flt(asset_value)

        # --- Step 4: Set the Calculated Values on the Parent Document ---
        self.total_animals = animal_count
        if animal_count > 0:
            self.average_age = round(total_age / animal_count, 2)
            self.average_weight = round(total_weight / animal_count, 2)
        self.total_asset_value = total_asset_value
