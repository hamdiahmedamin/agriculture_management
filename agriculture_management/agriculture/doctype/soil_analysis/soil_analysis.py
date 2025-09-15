# Copyright (c) 2017, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt


# soil_analysis.py
import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import get_datetime, flt


class SoilAnalysis(Document):
    def validate(self):
        """Validates datetime sequence."""
        if self.collection_datetime and self.laboratory_testing_datetime:
            if get_datetime(self.collection_datetime) > get_datetime(self.laboratory_testing_datetime):
                frappe.throw(
                    _('Laboratory Testing Datetime cannot be before Collection Datetime'))
        if self.laboratory_testing_datetime and self.result_datetime:
            if get_datetime(self.laboratory_testing_datetime) > get_datetime(self.result_datetime):
                frappe.throw(
                    _('Result Datetime cannot be before Laboratory Testing Datetime'))

    def before_save(self):
        """Recalculate ratios before every save."""
        self.recalculate_ratios()

    @frappe.whitelist()
    def load_contents(self):
        # Your existing load_contents function is great.
        docs = frappe.get_all("Agriculture Analysis Criteria", filters={
                              'linked_doctype': 'Soil Analysis'})
        for doc in docs:
            self.append('soil_analysis_criteria', {'title': str(doc.name)})

    @frappe.whitelist()
    def recalculate_ratios(self):
        """
        Calculates soil nutrient ratios based on values in the child table.
        This brings your read-only calculation fields to life.
        """
        # Create a dictionary of the criteria results for easy lookup
        results = {row.title: flt(row.result)
                   for row in self.soil_analysis_criteria}

        # Get the values for Calcium (Ca), Potassium (K), and Magnesium (Mg)
        # IMPORTANT: The 'title' must exactly match the title in 'Agriculture Analysis Criteria'
        ca = results.get("Calcium (Ca)", 0.0)
        k = results.get("Potassium (K)", 0.0)
        mg = results.get("Magnesium (Mg)", 0.0)

        # Perform calculations, avoiding division by zero
        self.ca_per_k = ca / k if k else 0
        self.ca_per_mg = ca / mg if mg else 0
        self.mg_per_k = mg / k if k else 0
        self.ca_mg_per_k = (ca + mg) / k if k else 0
