# Copyright (c) 2025, aminos and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.utils import nowdate, getdate, date_diff

# This class defines the server-side controller for the Livestock DocType
class Livestock(Document):
    # This is a "hook" that runs automatically before the document is saved
    def before_save(self):
        """
        Calculates the age of the animal based on the Date of Birth.
        'self' refers to the document instance (e.g., the specific animal's record).
        """
        if self.date_of_birth:
            # Calculate the difference in days between today and the date of birth
            age_in_days = date_diff(nowdate(), self.date_of_birth)
            
            # Convert days to years for the 'age' field
            # We assume the 'age' field is a Float type
            self.age = round(age_in_days / 365.25, 2)
            
        # --- Auto-update Current Weight ---
        if self.weight_history:
            # Sort the history by date, latest first
            sorted_history = sorted(self.weight_history, key=lambda row: getdate(row.date), reverse=True)
            # Set the current_weight to the weight from the most recent entry
            self.current_weight = sorted_history[0].weight
        
        self.calculate_genetic_index()
    
    def validate(self):
        # --- Run the age calculation first to ensure self.age is up to date ---
        if self.date_of_birth:
            self.age = round(date_diff(nowdate(), self.date_of_birth) / 365.25, 2)
        
        # --- Validate Sire (Father) ---
        if self.sire_father:
            sire_doc = frappe.get_doc("Livestock", self.sire_father)
            if sire_doc.date_of_birth and self.date_of_birth:
                if getdate(sire_doc.date_of_birth) >= getdate(self.date_of_birth):
                    frappe.throw(f"Sire (Father) <b>{self.sire_father}</b> cannot be younger than or the same age as the animal.")

        # --- Validate Dam (Mother) ---
        if self.dam_mother:
            dam_doc = frappe.get_doc("Livestock", self.dam_mother)
            if dam_doc.date_of_birth and self.date_of_birth:
                if getdate(dam_doc.date_of_birth) >= getdate(self.date_of_birth):
                    frappe.throw(f"Dam (Mother) <b>{self.dam_mother}</b> cannot be younger than or the same age as the animal.")
                    
    def on_update(self):
        inactive_statuses = ["Deceased", "Culled", "Sold"]
        if self.status in inactive_statuses:
            # --- Update the linked Asset ---
            if self.asset:
                asset_doc = frappe.get_doc("Asset", self.asset)
                if asset_doc.docstatus == 1: # If asset is submitted (not already disposed)
                    # This requires more complex logic to create a disposal Journal Entry
                    # For now, we can set the status to "Scrapped" if not sold
                    if self.status in ["Deceased", "Culled"]:
                        asset_doc.status = "Scrapped"
                        # Ideally, you'd call a method here to also create a GL Entry to write off the value
                        # For example: self.create_asset_disposal_entry(asset_doc)
                        asset_doc.save(ignore_permissions=True)
                        frappe.msgprint(f"Asset {self.asset} status updated to Scrapped.")

            # --- Update the linked Serial No ---
            if self.serial_no:
                serial_no_doc = frappe.get_doc("Serial No", self.serial_no)
                if serial_no_doc.status != "Inactive":
                    serial_no_doc.status = "Inactive"
                    serial_no_doc.save(ignore_permissions=True)
                    frappe.msgprint(f"Serial No {self.serial_no} status updated to Inactive.")
    
    def calculate_genetic_index(self):
        """
        Calculates a weighted score based on the traits in the child table.
        """
        # --- DEBUG 1: See if genetic_traits is empty ---      
        if not self.genetic_traits:
            self.genetic_index = 0.0
            return

        total_weighted_score = 0.0
        
        # Get the list of trait names from the child table
        trait_names = [d.trait for d in self.genetic_traits if d.trait]
        # --- DEBUG 2: See the trait names being processed ---
        if not trait_names:
            self.genetic_index = 0.0
            return

        trait_weightings = frappe.get_all("Trait", 
            filters={"name": ("in", trait_names)},
            fields=["name", "weighting_factor"]
        )
        
        # --- DEBUG 3: See the trait weightings fetched from the database ---

        weighting_map = {d.name: d.weighting_factor for d in trait_weightings}
        
        
        # --- DEBUG 4: See the weighting map ---
        for trait_row in self.genetic_traits:
            weighting = weighting_map.get(trait_row.trait, 0.0) # Default to 0.0 to be safe
            value = trait_row.value or 0.0
            
            # --- DEBUG 5: See the calculation for each row ---
            total_weighted_score += value * weighting

        # --- DEBUG 6: See the final score before averaging ---

        if len(self.genetic_traits) > 0:
            self.genetic_index = round(total_weighted_score / len(self.genetic_traits), 2)
        else:
            self.genetic_index = 0.0