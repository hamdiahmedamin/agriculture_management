# soil_texture.py
import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt, get_datetime
import json


class SoilTexture(Document):
    def validate(self):
        """
        This hook runs before every save and is the final authority on data integrity.
        """
        # --- 1. DATETIME VALIDATION (from before) ---
        if self.collection_datetime and self.laboratory_testing_datetime:
            if get_datetime(self.collection_datetime) > get_datetime(self.laboratory_testing_datetime):
                frappe.throw(
                    _('Laboratory Testing Datetime cannot be before Collection Datetime'))

        if self.laboratory_testing_datetime and self.result_datetime:
            if get_datetime(self.laboratory_testing_datetime) > get_datetime(self.result_datetime):
                frappe.throw(
                    _('Result Datetime cannot be before Laboratory Testing Datetime'))

        # --- 2. NEW SERVER-SIDE PERCENTAGE VALIDATION ---
        # This is the crucial backend check.
        clay = flt(self.clay_composition)
        sand = flt(self.sand_composition)
        silt = flt(self.silt_composition)

        # Round to 2 decimal places for precision
        total = round(clay + sand + silt, 2)

        if total != 100.0:
            # If the total is not exactly 100, block the save and inform the user.
            frappe.throw(
                _(f"The sum of Clay ({clay}%), Sand ({sand}%), and Silt ({silt}%) must be exactly 100%. "
                  f"Current total is {total}%."),
                title="Composition Error"
            )

    @frappe.whitelist()
    def load_contents(self):
        # This function is correct and remains.
        docs = frappe.get_all("Agriculture Analysis Criteria", filters={
                              'linked_doctype': 'Soil Texture'})
        for doc in docs:
            self.append('soil_texture_criteria', {'title': str(doc.name)})

# =====================================================================
# === THIS IS THE NEW, SIMPLIFIED STANDALONE FUNCTION ===
# =====================================================================


@frappe.whitelist()
def get_soil_type_from_composition(data):
    """
    Accepts a JSON string of balanced percentages and returns the calculated soil type.
    """
    if isinstance(data, str):
        data = json.loads(data)

    c = flt(data.get('clay_composition'))
    sa = flt(data.get('sand_composition'))
    si = flt(data.get('silt_composition'))

    # --- The Core USDA Calculation Logic (Unchanged and correct) ---
    if si + (1.5 * c) < 15:
        return 'Sand'
    elif si + 1.5 * c >= 15 and si + 2 * c < 30:
        return 'Loamy Sand'
    elif ((c >= 7 and c < 20) or (sa > 52) and ((si + 2*c) >= 30) or (c < 7 and si < 50 and (si+2*c) >= 30)):
        return 'Sandy Loam'
    elif ((c >= 7 and c < 27) and (si >= 28 and si < 50) and (sa <= 52)):
        return 'Loam'
    elif ((si >= 50 and (c >= 12 and c < 27)) or ((si >= 50 and si < 80) and c < 12)):
        return 'Silt Loam'
    elif (si >= 80 and c < 12):
        return 'Silt'
    elif ((c >= 20 and c < 35) and (si < 28) and (sa > 45)):
        return 'Sandy Clay Loam'
    elif ((c >= 27 and c < 40) and (sa > 20 and sa <= 45)):
        return 'Clay Loam'
    elif ((c >= 27 and c < 40) and (sa <= 20)):
        return 'Silty Clay Loam'
    elif (c >= 35 and sa > 45):
        return 'Sandy Clay'
    elif (c >= 40 and si >= 40):
        return 'Silty Clay'
    elif (c >= 40 and sa <= 45 and si < 40):
        return 'Clay'
    else:
        return 'Select'
