# Copyright (c) 2017, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt


# plant_analysis.py
import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import get_datetime


class PlantAnalysis(Document):
    def validate(self):
        """
        Validates that the datetime fields are in a logical sequence.
        """
        # Check 1: Lab testing must be after collection
        if self.collection_datetime and self.laboratory_testing_datetime:
            if get_datetime(self.collection_datetime) > get_datetime(self.laboratory_testing_datetime):
                frappe.throw(
                    _('Laboratory Testing Datetime cannot be before Collection Datetime'))

        # Check 2: Lab result must be after testing
        if self.laboratory_testing_datetime and self.result_datetime:
            if get_datetime(self.laboratory_testing_datetime) > get_datetime(self.result_datetime):
                frappe.throw(
                    _('Result Datetime cannot be before Laboratory Testing Datetime'))

    @frappe.whitelist()
    def load_contents(self):
        # Your existing load_contents function is great and remains here.
        docs = frappe.get_all("Agriculture Analysis Criteria", filters={
                              'linked_doctype': 'Plant Analysis'})
        for doc in docs:
            self.append('plant_analysis_criteria', {'title': str(doc.name)})
