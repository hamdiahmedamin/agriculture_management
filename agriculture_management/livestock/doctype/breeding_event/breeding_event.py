# breeding_event.py
import frappe
from frappe.model.document import Document
from frappe.utils import nowdate, getdate


class BreedingEvent(Document):

    def validate(self):
        """
        This hook runs on every save, before 'before_save'.
        It's the perfect place to validate data integrity.
        """
        # --- THIS IS THE NEW GENDER VALIDATION BLOCK ---
        if self.dam and self.sire:
            # Fetch the gender of both the Dam and the Sire in a single, efficient query
            parent_genders = frappe.get_all(
                "Animal",
                filters={"name": ["in", [self.dam, self.sire]]},
                fields=["name", "gender"]
            )

            # Create a map for easy lookup
            gender_map = {d.name: d.gender for d in parent_genders}

            # Check the Dam's gender
            if gender_map.get(self.dam) != "Female":
                frappe.throw(
                    f"<b>{self.dam}</b> is not a Female and cannot be selected as a Dam.")

            # Check the Sire's gender
            if gender_map.get(self.sire) != "Male":
                frappe.throw(
                    f"<b>{self.sire}</b> is not a Male and cannot be selected as a Sire.")
        # --- END OF VALIDATION BLOCK ---

    def before_save(self):
        """
        This hook runs after validate() and before the document is written to the database.
        It orchestrates all automatic calculations and status updates.
        """
        self.set_dynamic_status()
        self.calculate_due_date()
        self.create_offspring_if_successful()

    def set_dynamic_status(self):
        """Sets the Status field based on Outcome and Breeding Date."""
        if self.outcome in ["Successful", "Failed", "Miscarriage/Aborted"]:
            self.status = "Completed"
            return

        if self.outcome in ["In Progress", "Pending"]:
            if getdate(self.breeding_date) > getdate(nowdate()):
                self.status = "Planned"
            else:
                self.status = "In Progress"

    def calculate_due_date(self):
        """Calculates and sets the expected due date."""
        if self.dam and self.breeding_date:
            dam_species = frappe.db.get_value("Animal", self.dam, "species")
            if dam_species:
                gestation_days = frappe.db.get_value(
                    "Livestock Species", dam_species, "gestation_period_days") or 0
                new_due_date = frappe.utils.add_days(
                    self.breeding_date, gestation_days)
                if self.expected_due_date != new_due_date:
                    self.expected_due_date = new_due_date

    def create_offspring_if_successful(self):
        """
        If the outcome is 'Successful' and an offspring has not been created yet,
        this method creates the new Animal document.
        """
        if self.outcome == 'Successful' and not self.offspring:
            if not all([self.offspring_id, self.offspring_gender, self.birth_date]):
                frappe.throw(
                    "For a 'Successful' outcome, please provide the Offspring ID, Gender, and Actual Birth Date.")

            new_animal = self.create_new_offspring_animal()
            self.offspring = new_animal.name

    def create_new_offspring_animal(self):
        """Creates and returns a new Animal document based on the event data."""
        if frappe.db.exists("Animal", self.offspring_id):
            frappe.throw(
                f"An Animal with the ID '{self.offspring_id}' already exists.")

        dam_data = frappe.get_value(
            "Animal", self.dam, ["species", "breed", "location_pen"], as_dict=1)

        new_animal = frappe.get_doc({
            "doctype": "Animal",
            "animal_id_tag_id": self.offspring_id,
            "gender": self.offspring_gender,
            "date_of_birth": self.birth_date,
            "acquisition_type": "Birth",
            "dam_mother": self.dam,
            "sire_father": self.sire,
            "species": dam_data.species,
            "breed": dam_data.breed,
            "location_pen": dam_data.location_pen,
            "status": "Active"
        })
        new_animal.insert(ignore_permissions=True)
        frappe.msgprint(
            f"New offspring animal <a href='/app/animal/{new_animal.name}'>{new_animal.name}</a> created successfully.", indicator='green', title='Offspring Created')
        return new_animal
