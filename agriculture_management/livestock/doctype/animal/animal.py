# Copyright (c) 2025, aminos and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.utils import nowdate, getdate, date_diff, flt
from frappe import _


class Animal(Document):

    def before_save(self):
        """
        Set calculated values and enforce data consistency before saving.
        """
        # --- 1. Calculate Age ---
        new_age = 0.0
        if self.date_of_birth:
            new_age = round(
                date_diff(nowdate(), self.date_of_birth) / 365.25, 2)
        if self.age != new_age:
            self.age = new_age

        # --- 2. Auto-update Current Weight ---
        if self.weight_history:
            sorted_history = sorted(
                self.weight_history, key=lambda row: getdate(row.date), reverse=True)
            latest_weight = sorted_history[0].weight_kg
            if self.current_weight != latest_weight:
                self.current_weight = latest_weight

        # --- 3. Calculate Genetic Index ---
        self.calculate_genetic_index()

        # --- 4. NEW: Cleanup Logic for ERP Integration Fields ---
        # If 'Is Asset' is unchecked, ensure the 'asset' link field is cleared.
        if not self.is_asset:
            self.asset = None

        # If 'Is Serialized Item' is unchecked, ensure all related fields are cleared.
        if not self.is_serialized_item:
            self.item_code = None
            self.serial_no = None

    def validate(self):
        """
        This hook runs every time the document is saved.
        It provides the ultimate guarantee of data integrity.
        """
        # --- THIS IS THE SERVER-SIDE GUARANTEE ---
        if self.species and self.livestock_group:
            # Fetch the species of the selected Livestock Group from the database.
            group_species = frappe.db.get_value(
                "Livestock Group", self.livestock_group, "species")

            # If the group's species doesn't match the animal's species, block the save.
            if group_species and group_species != self.species:
                frappe.throw(
                    title="Species Mismatch",
                    msg=f"Cannot assign this animal to Livestock Group <b>{self.livestock_group}</b>.<br><br>"
                    f"The animal's species is <b>{self.species}</b>, but the group's species is <b>{group_species}</b>."
                )

        # --- Validate Parents' Age ---
        if self.sire_father or self.dam_mother:
            parent_ids = list(
                filter(None, [self.sire_father, self.dam_mother]))
            if not parent_ids:
                return

            parent_birth_dates = frappe.get_list(
                "Animal", filters={"name": ["in", parent_ids]}, fields=["name", "date_of_birth"])
            for parent in parent_birth_dates:
                if parent.date_of_birth and self.date_of_birth and (getdate(parent.date_of_birth) >= getdate(self.date_of_birth)):
                    parent_role = "Sire (Father)" if parent.name == self.sire_father else "Dam (Mother)"
                    frappe.throw(
                        f"{parent_role} <b>{parent.name}</b> cannot be younger than the animal.")

    def on_update(self):
        inactive_statuses = ["Deceased", "Culled", "Sold"]
        if not self.is_new() and self.has_value_changed("status") and self.status in inactive_statuses:
            if self.asset:
                asset = frappe.get_doc("Asset", self.asset)
                if asset.docstatus == 1 and self.status in ["Deceased", "Culled"]:
                    asset.status = "Scrapped"
                    asset.save(ignore_permissions=True)
                    frappe.msgprint(
                        f"Asset {self.asset} status updated to Scrapped.")
            if self.serial_no:
                serial_no = frappe.get_doc("Serial No", self.serial_no)
                if serial_no.status != "Inactive":
                    serial_no.status = "Inactive"
                    serial_no.save(ignore_permissions=True)
                    frappe.msgprint(
                        f"Serial No {self.serial_no} status updated to Inactive.")

    def calculate_genetic_index(self):
        if not self.genetic_traits:
            self.genetic_index = 0.0
            return

        trait_names = [d.trait for d in self.genetic_traits if d.trait]
        if not trait_names:
            self.genetic_index = 0.0
            return

        trait_weightings = frappe.get_all("Trait", filters={"name": (
            "in", trait_names)}, fields=["name", "weighting_factor"])
        weighting_map = {d.name: d.weighting_factor for d in trait_weightings}

        total_weighted_score = sum((trait_row.value or 0.0) * weighting_map.get(
            trait_row.trait, 0.0) for trait_row in self.genetic_traits)

        if len(self.genetic_traits) > 0:
            new_index = round(total_weighted_score /
                              len(self.genetic_traits), 2)
            if self.genetic_index != new_index:
                self.genetic_index = new_index
        else:
            self.genetic_index = 0.0

    @frappe.whitelist()
    def record_direct_feed(self, feed_item, quantity, source_warehouse):
        """
        Records a direct, unscheduled feeding for this specific animal.
        """
        if not self.livestock_group:
            frappe.throw(
                _("This animal is not assigned to a Livestock Group. Cannot determine Cost Center."))

        # 1. Create the Material Issue Stock Entry
        se = frappe.get_doc({
            "doctype": "Stock Entry",
            "purpose": "Material Issue",
            "stock_entry_type": "Material Issue",
            "set_posting_time": 1,
            "posting_date": nowdate(),
            "custom_livestock_group": self.livestock_group,
            "items": [{
                "item_code": feed_item,
                "qty": flt(quantity),
                "s_warehouse": source_warehouse,
                "cost_center": frappe.db.get_value("Livestock Group", self.livestock_group, "cost_center"),
                "custom_livestock_group": self.livestock_group
            }]
        })
        se.insert(ignore_permissions=True)
        se.submit()

        # 2. Add a log entry to this animal's child table
        self.append("animal_feeding_log", {
            "date": nowdate(),
            "description": f"Direct feed: {flt(quantity):.2f} Kg of {feed_item}",
            "quantity_consumed_est": quantity,
            "source_doctype": "Stock Entry",
            "source_document": se.name
        })
        self.save(ignore_permissions=True)

        frappe.msgprint(
            _("Direct feed recorded via Stock Entry <a href='/app/stock-entry/{0}'>{0}</a>.")
            .format(se.name), title=_("Feeding Recorded"), indicator='green'
        )
        return se.name
