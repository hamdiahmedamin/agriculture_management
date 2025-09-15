# Copyright (c) 2025, aminos and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.utils import flt, nowdate, getdate
from frappe import _


class LivestockGroup(Document):
    def validate(self):
        """
        Runs on every save to guarantee data integrity.
        1. Checks for duplicate animals in the list.
        2. Ensures all animals in the list match the group's species.
        """
        if not self.is_flock and self.animal_list:
            seen_animals = set()
            duplicates = [
                row.animal for row in self.animal_list if row.animal in seen_animals or seen_animals.add(row.animal)]
            if duplicates:
                frappe.throw(
                    f"Duplicate animals found in the list: {', '.join(list(set(duplicates)))}")

            animal_names = [
                row.animal for row in self.animal_list if row.animal]
            if not animal_names:
                return

            mismatched_animals = frappe.get_all("Animal",
                                                filters={"name": ["in", animal_names], "species": [
                                                    "!=", self.species]},
                                                fields=["name", "species"])
            if mismatched_animals:
                error_msg = f"Animals' species must match the group's species (<b>{self.species}</b>):<br><ul>"
                for animal in mismatched_animals:
                    error_msg += f"<li><b>{animal.name}</b> (Species: {animal.species})</li>"
                error_msg += "</ul>"
                frappe.throw(error_msg, title="Species Mismatch")

    def before_save(self):
        """This is the single source of truth for calculating statistics. It runs automatically on every save."""
        self.recalculate_stats()

    def on_update(self):
        """After saving, push changes down to member documents."""
        self.sync_animal_group_membership()
        self.sync_member_locations_with_stock_transfer()
        self.sync_member_status()

    @frappe.whitelist()
    def sync_with_poultry_flock(self):
        """
        Pulls all key data from the linked Poultry Flock document and updates
        this Livestock Group to match.
        """
        if not self.is_flock or not self.poultry_flock:
            frappe.throw(_("Please link a Poultry Flock to synchronize."))

        flock_data = frappe.db.get_value(
            "Poultry Flock",
            self.poultry_flock,
            ["current_head_count", "age_in_days",
                "average_body_weight", "coop", "status", "specie"],
            as_dict=True
        )

        if not flock_data:
            frappe.throw(
                _("Could not find the linked Poultry Flock document."))

        self.group_location = flock_data.get("coop")
        self.status = flock_data.get("status")
        self.species = flock_data.get("specie")
        self.save(ignore_permissions=True)
        frappe.msgprint(
            _("Group synchronized with <b>{0}</b>.").format(self.poultry_flock), indicator='green')

    def recalculate_stats(self):
        """Polymorphic function to calculate stats for either flocks or individuals."""
        if self.is_flock:
            if self.poultry_flock:
                flock_stats = frappe.db.get_value("Poultry Flock", self.poultry_flock,
                                                  ["current_head_count", "age_in_days", "average_body_weight"], as_dict=True)
                if flock_stats:
                    self.total_animals = flock_stats.get(
                        "current_head_count") or 0
                    self.average_age = flt(flock_stats.get("age_in_days"))
                    self.average_weight = flt(
                        flock_stats.get("average_body_weight"))
                else:
                    self.total_animals, self.average_age, self.average_weight = 0, 0.0, 0.0
            else:
                self.total_animals, self.average_age, self.average_weight = 0, 0.0, 0.0
        else:
            if not self.animal_list:
                self.total_animals, self.average_age, self.average_weight = 0, 0.0, 0.0
                return
            animal_names = [
                row.animal for row in self.animal_list if row.animal]
            if not animal_names:
                self.total_animals, self.average_age, self.average_weight = 0, 0.0, 0.0
                return
            animal_data = frappe.get_all("Animal", filters={
                                         "name": ["in", animal_names]}, fields=["age", "current_weight"])
            if not animal_data:
                self.total_animals, self.average_age, self.average_weight = 0, 0.0, 0.0
                return
            total_age = sum(flt(d.get("age")) for d in animal_data)
            total_weight = sum(flt(d.get("current_weight"))
                               for d in animal_data)
            animal_count = len(animal_data)
            self.total_animals = animal_count
            self.average_age = round(
                total_age / animal_count, 2) if animal_count else 0.0
            self.average_weight = round(
                total_weight / animal_count, 2) if animal_count else 0.0

    def sync_animal_group_membership(self):
        if self.is_flock:
            return
        current_animals = {
            row.animal for row in self.animal_list if row.animal}
        previous_animals = set()
        original_doc = self.get_doc_before_save()
        if original_doc and original_doc.animal_list:
            previous_animals = {
                row.animal for row in original_doc.animal_list if row.animal}
        if current_animals == previous_animals:
            return
        animals_to_clear = previous_animals - current_animals
        for animal_name in animals_to_clear:
            frappe.db.set_value("Animal", animal_name, "livestock_group", None)
        if current_animals:
            for animal_name in current_animals:
                frappe.db.set_value("Animal", animal_name,
                                    "livestock_group", self.name)
            frappe.msgprint(_("Updated group assignment for {0} animals.").format(
                len(current_animals)), indicator='green')

    def sync_member_status(self):
        original_doc = self.get_doc_before_save()
        if not original_doc or self.status == original_doc.status:
            return
        if self.is_flock:
            if self.poultry_flock:
                frappe.db.set_value(
                    "Poultry Flock", self.poultry_flock, "status", self.status)
        else:
            animal_names = [
                row.animal for row in self.animal_list if row.animal]
            if animal_names:
                frappe.db.set_value("Animal", {
                                    "name": ["in", animal_names]}, "status", self.status, update_modified=False)
        frappe.msgprint(
            _("Status for all members updated to <b>{0}</b>.").format(self.status), indicator='green')

    def sync_member_locations_with_stock_transfer(self):
        original_doc = self.get_doc_before_save()
        if not original_doc or self.group_location == original_doc.group_location:
            return
        old_location, new_location = original_doc.group_location, self.group_location
        if not old_location:
            self.update_member_location_fields(new_location)
            return

        se = frappe.get_doc({
            "doctype": "Stock Entry",
            "stock_entry_type": "Material Transfer",  # Critical fix
            "purpose": "Material Transfer",
            "set_posting_time": 1,
            "posting_date": nowdate(),
            "custom_livestock_group": self.name
        })

        if self.is_flock:
            flock_data = frappe.db.get_value("Poultry Flock", {"livestock_group": self.name}, [
                                             "item", "current_head_count", "batch"], as_dict=True)
            if flock_data and flt(flock_data.current_head_count) > 0:
                se.append("items", {"item_code": flock_data.item, "qty": flock_data.current_head_count, "s_warehouse": old_location,
                          "t_warehouse": new_location, "use_serial_batch_fields": 1, "batch_no": flock_data.batch, "custom_livestock_group": self.name})
        else:
            animal_names = [
                row.animal for row in self.animal_list if row.animal]
            if animal_names:
                animal_details = frappe.get_all("Animal", filters={"name": [
                                                "in", animal_names], "serial_no": ["!=", ""]}, fields=["item", "serial_no"])
                for animal in animal_details:
                    se.append("items", {"item_code": animal.item, "qty": 1, "s_warehouse": old_location,
                              "t_warehouse": new_location, "serial_no": animal.serial_no, "custom_livestock_group": self.name})

        if not se.items:
            self.update_member_location_fields(new_location)
            frappe.msgprint(
                _("Group location updated. No stock items found to transfer."))
            return
        try:
            se.insert(ignore_permissions=True)
            se.submit()
            self.update_member_location_fields(new_location)
            frappe.msgprint(_("Stock moved via Stock Entry <a href='/app/stock-entry/{0}'><b>{0}</b></a>.").format(
                se.name), title=_("Stock Transferred"), indicator='green')
        except Exception as e:
            frappe.log_error(frappe.get_traceback())
            frappe.throw(
                _("Could not complete stock transfer. Error: {0}").format(e))

    def update_member_location_fields(self, new_location):
        if self.is_flock:
            if self.poultry_flock:
                frappe.db.set_value(
                    "Poultry Flock", self.poultry_flock, "coop", new_location)
        else:
            animal_names = [
                row.animal for row in self.animal_list if row.animal]
            if animal_names:
                frappe.db.set_value("Animal", {"name": [
                                    "in", animal_names]}, "location_pen", new_location, update_modified=False)

    @frappe.whitelist()
    def record_direct_feed(self, feed_item, quantity, source_warehouse):
        """
        Records a direct, unscheduled feeding for a group of individual animals
        from a user-specified source warehouse.
        """
        if self.is_flock:
            frappe.throw(
                _("Direct feeds for flocks should be recorded from the Poultry Flock form."))
        if not self.animal_list:
            frappe.throw(_("This group has no animals to feed."))

        # --- THIS IS THE DEFINITIVE FIX ---
        # The source_warehouse is now a required argument passed from the client.
        # No need to look up a default setting.
        if not source_warehouse:
            frappe.throw(
                _("A Source Warehouse is required to record a feeding."))
        # --- END OF FIX ---

        se = frappe.get_doc({
            "doctype": "Stock Entry",
            "stock_entry_type": "Material Issue",
            "purpose": "Material Issue",
            "set_posting_time": 1,
            "posting_date": nowdate(),
            "custom_livestock_group": self.name,
            "items": [{
                "item_code": feed_item,
                "qty": flt(quantity),
                "s_warehouse": source_warehouse,
                "cost_center": self.cost_center,
                "custom_livestock_group": self.name
            }]
        })

        se.insert(ignore_permissions=True)
        se.submit()

        # The logic to push the log to individual animals is unchanged and correct.
        head_count = len(self.animal_list)
        per_animal_qty = flt(quantity) / head_count
        for animal_member in self.animal_list:
            animal_doc = frappe.get_doc("Animal", animal_member.animal)
            animal_doc.append("animal_feeding_log", {
                "date": nowdate(),
                "description": f"Direct feed: {flt(per_animal_qty):.2f} Kg of {feed_item}",
                "quantity_consumed_est": per_animal_qty,
                "source_doctype": "Stock Entry",
                "source_document": se.name
            })
            animal_doc.save(ignore_permissions=True)

        frappe.msgprint(
            _("Direct feed recorded via Stock Entry <a href='/app/stock-entry/{0}'>{0}</a> and updated on {1} animals.")
            .format(se.name, head_count),
            title=_("Feeding Complete"), indicator='green'
        )
        return se.name

    # This is a whitelisted method that the JS was trying to call. It is no longer needed
    # because before_save handles the calculation automatically, but we leave it here
    # in case it is used elsewhere. It now returns the calculated values instead of setting them.
    @frappe.whitelist()
    def calculate_and_get_statistics(self):
        stats = {"total_animals": 0, "average_age": 0.0, "average_weight": 0.0}
        if self.is_flock:
            if self.poultry_flock:
                flock_stats = frappe.db.get_value("Poultry Flock", self.poultry_flock, [
                                                  "current_head_count", "age_in_days", "average_body_weight"], as_dict=True)
                if flock_stats:
                    stats["total_animals"] = flock_stats.get(
                        "current_head_count") or 0
                    stats["average_age"] = flt(flock_stats.get("age_in_days"))
                    stats["average_weight"] = flt(
                        flock_stats.get("average_body_weight"))
        else:
            if self.animal_list:
                animal_names = [
                    row.animal for row in self.animal_list if row.animal]
                if animal_names:
                    animal_data = frappe.get_all("Animal", filters={
                                                 "name": ["in", animal_names]}, fields=["age", "current_weight"])
                    if animal_data:
                        total_age = sum(flt(d.get("age")) for d in animal_data)
                        total_weight = sum(flt(d.get("current_weight"))
                                           for d in animal_data)
                        animal_count = len(animal_data)
                        stats["total_animals"] = animal_count
                        stats["average_age"] = round(
                            total_age / animal_count, 2) if animal_count else 0.0
                        stats["average_weight"] = round(
                            total_weight / animal_count, 2) if animal_count else 0.0
        return stats
