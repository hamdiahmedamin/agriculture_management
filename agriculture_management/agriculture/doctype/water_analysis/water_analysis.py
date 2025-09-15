# Copyright (c) 2017, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt


import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import get_datetime  # Import the get_datetime utility


class WaterAnalysis(Document):
    @frappe.whitelist()
    def load_contents(self):
        docs = frappe.get_all("Agriculture Analysis Criteria", filters={
                              'linked_doctype': 'Water Analysis'})
        for doc in docs:
            self.append('water_analysis_criteria', {'title': str(doc.name)})

    @frappe.whitelist()
    def update_lab_result_date(self):
        if not self.result_datetime:
            self.result_datetime = self.laboratory_testing_datetime

    # =====================================================================
    # === THIS IS THE CORRECTED VALIDATE METHOD ===
    # =====================================================================
    def validate(self):
        """
        Validates that the datetime fields are in a logical sequence,
        but only if the fields have been filled out.
        """
        # Check 1: Lab testing must be after collection
        # This condition is now "safe" because it checks for existence first.
        if self.collection_datetime and self.laboratory_testing_datetime:
            # Use get_datetime for robust comparison
            if get_datetime(self.collection_datetime) > get_datetime(self.laboratory_testing_datetime):
                frappe.throw(
                    _('Lab testing datetime cannot be before collection datetime'))

        # Check 2: Lab result must be after testing
        # This condition is also now safe.
        if self.laboratory_testing_datetime and self.result_datetime:
            if get_datetime(self.laboratory_testing_datetime) > get_datetime(self.result_datetime):
                frappe.throw(
                    _('Lab result datetime cannot be before testing datetime'))
