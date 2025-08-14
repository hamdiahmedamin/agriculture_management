# Copyright (c) 2025, aminos and contributors
# For license information, please see license.txt

      
import frappe
from frappe.model.document import Document

class LivestockGroup(Document):
    def before_save(self):
        """
        Calculates and sets dashboard statistics for the group before saving.
        """
        if not self.animal_list:
            self.total_animals = 0
            self.average_age = 0.0
            self.average_weight = 0.0
            return

        total_age = 0.0
        total_weight = 0.0
        animal_count = len(self.animal_list)

        for animal_row in self.animal_list:
            # Fetch the full document for each animal to get its properties
            animal_doc = frappe.get_doc("Livestock", animal_row.animal)
            total_age += animal_doc.age or 0.0
            total_weight += animal_doc.current_weight or 0.0
        
        self.total_animals = animal_count
        self.average_age = round(total_age / animal_count, 2) if animal_count else 0.0
        self.average_weight = round(total_weight / animal_count, 2) if animal_count else 0.0

    