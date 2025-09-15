# Copyright (c) 2025, aminos and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.utils import flt, date_diff, getdate
from datetime import timedelta
from frappe import _


class FeedingSchedule(Document):
    def validate(self):
        """Validate data before saving."""
        if self.from_date and self.to_date and getdate(self.from_date) > getdate(self.to_date):
            frappe.throw(_("From Date cannot be after To Date."))

        if self.livestock_group and self.from_date and self.to_date:
            overlapping_schedules = frappe.db.sql("""
                SELECT name FROM `tabFeeding Schedule`
                WHERE livestock_group = %(group)s AND name != %(current_doc)s AND docstatus < 2
                AND (from_date <= %(to_date)s AND to_date >= %(from_date)s)
            """, {"group": self.livestock_group, "current_doc": self.name, "from_date": self.from_date, "to_date": self.to_date}, as_list=1)

            if overlapping_schedules:
                overlapping_list = [item[0] for item in overlapping_schedules]
                frappe.throw(
                    _("Date range overlaps with existing schedule(s): {0}")
                    .format(", ".join([f"<a href='/app/feeding-schedule/{s}'>{s}</a>" for s in overlapping_list])),
                    title=_("Overlapping Schedule")
                )

    @frappe.whitelist()
    def generate_feeding_log(self):
        """Populates the child table. Handles both flocks and animal groups."""
        if not all([self.livestock_group, self.from_date, self.to_date, self.feed_formulation]):
            frappe.throw(
                _("Livestock Group, Date Range, and Feed Formulation are required."))

        group = frappe.get_doc("Livestock Group", self.livestock_group)
        self.feeding_schedule_log = []

        if group.is_flock:
            self.generate_log_for_flock(group)
        else:
            self.generate_log_for_animal_group(group)

        if not self.feeding_schedule_log:
            frappe.msgprint(
                _("No valid feeding entries could be generated for the given criteria."))
            return

        self.status = "Generated"
        self.save()
        frappe.msgprint(_("Feeding schedule has been successfully generated."))

    def generate_log_for_flock(self, group):
        flock = self.get_linked_flock(group.name)
        for schedule_date in self.get_date_range():
            age_in_days = date_diff(schedule_date, flock.hatch_date)
            if age_in_days < 0:
                continue
            daily_intake = self.get_daily_intake_for_age(
                flock.performance_standard, age_in_days)
            if not daily_intake:
                continue
            total_feed_grams = flt(daily_intake) * \
                flt(flock.current_head_count)
            total_feed_kg = total_feed_grams / 1000
            self.append("feeding_schedule_log", {
                        "date": schedule_date, "age_in_days": age_in_days, "recommended_quantity": total_feed_kg, "status": "Planned"})

    def generate_log_for_animal_group(self, group):
        if not group.animal_list:
            frappe.throw(
                _("The selected Livestock Group has no animals in its list."))
        animal_names = [d.animal for d in group.animal_list]
        animal_birth_dates = frappe.get_all("Animal", filters={
                                            "name": ["in", animal_names]}, fields=["name", "date_of_birth"], as_list=True)
        birth_date_map = {name: dob for name, dob in animal_birth_dates}
        head_count = len(birth_date_map)
        performance_standard = group.performance_standard
        if not performance_standard:
            frappe.throw(
                _("Please link a Performance Standard to the Livestock Group '{0}'.").format(group.name))
        for schedule_date in self.get_date_range():
            total_age_on_day = 0
            for animal_name in animal_names:
                dob = birth_date_map.get(animal_name)
                if dob:
                    total_age_on_day += date_diff(schedule_date, dob)
            average_age_on_day = int(
                total_age_on_day / head_count) if head_count else 0
            if average_age_on_day < 0:
                continue
            daily_intake = self.get_daily_intake_for_age(
                performance_standard, average_age_on_day)
            if not daily_intake:
                continue
            total_feed_grams = flt(daily_intake) * head_count
            total_feed_kg = total_feed_grams / 1000
            self.append("feeding_schedule_log", {
                        "date": schedule_date, "age_in_days": average_age_on_day, "recommended_quantity": total_feed_kg, "status": "Planned"})

    # --- THIS IS THE DEFINITIVE, CORRECTED METHOD ---
    @frappe.whitelist()
    def complete_feeding_for_row(self, row_name, source_warehouse):
        """
        Creates a 'Material Issue' Stock Entry for a single log row and
        pushes a log entry down to every individual animal in the group.
        """
        log_row = self.get("feeding_schedule_log", {"name": row_name})[0]
        if not log_row:
            frappe.throw(_("Schedule log row not found."))
        if log_row.status != "Planned":
            frappe.throw(_("This feeding has already been processed."))
        if not source_warehouse:
            frappe.throw(_("A source warehouse is required."))

        formulation = frappe.get_doc("Feed Formulation", self.feed_formulation)
        group = frappe.get_doc("Livestock Group", self.livestock_group)

        se = frappe.get_doc({"doctype": "Stock Entry", "purpose": "Material Issue", "stock_entry_type": "Material Issue", "set_posting_time": 1,
                            "posting_date": log_row.date, "custom_livestock_group": self.livestock_group, "custom_feeding_schedule": self.name})

        for ingredient in formulation.ingredients:
            qty_to_issue = (flt(log_row.recommended_quantity)
                            * flt(ingredient.percentage)) / 100
            if qty_to_issue > 0:
                se.append("items", {"item_code": ingredient.item, "qty": qty_to_issue,
                          "s_warehouse": source_warehouse, "cost_center": group.cost_center})

        if not se.items:
            frappe.throw(_("No ingredients found in the formulation."))

        se.insert(ignore_permissions=True)
        se.submit()

        log_row.status = "Completed"
        log_row.stock_entry = se.name
        self.update_overall_status()
        self.save(ignore_permissions=True)

        # Push the log entry down to individual animals
        if not group.is_flock and group.animal_list:
            head_count = len(group.animal_list)
            if head_count > 0:
                per_animal_qty = flt(log_row.recommended_quantity) / head_count
                description = f"Scheduled feed: {flt(per_animal_qty):.2f} Kg of {formulation.formulation_name}"
                for animal_member in group.animal_list:
                    animal_doc = frappe.get_doc("Animal", animal_member.animal)
                    animal_doc.append("animal_feeding_log", {"date": log_row.date, "description": description,
                                      "quantity_consumed_est": per_animal_qty, "source_doctype": "Feeding Schedule", "source_document": self.name})
                    animal_doc.save(ignore_permissions=True)
                frappe.msgprint(
                    _("Feeding history has been updated for {0} animals.").format(head_count))

        return se.name
    # --- END OF CORRECTION ---

    def update_overall_status(self):
        """Checks log rows and updates the parent's overall status."""
        if not self.feeding_schedule_log:
            self.status = "Draft"
            return
        statuses = {row.status for row in self.feeding_schedule_log}
        if "Planned" not in statuses:
            self.status = "Completed"
        elif "Completed" in statuses or "Skipped" in statuses:
            self.status = "Partially Completed"
        else:
            self.status = "Generated"

    # --- HELPER FUNCTIONS ---
    def get_date_range(self):
        from_date_obj, to_date_obj = getdate(
            self.from_date), getdate(self.to_date)
        current_date = from_date_obj
        date_list = []
        while current_date <= to_date_obj:
            date_list.append(current_date)
            current_date += timedelta(days=1)
        return date_list

    def get_linked_flock(self, group_name):
        flock_name = frappe.db.get_value(
            "Poultry Flock", {"livestock_group": group_name}, "name")
        if not flock_name:
            frappe.throw(
                _("Livestock Group is not linked to an active Poultry Flock."))
        return frappe.get_doc("Poultry Flock", flock_name)

    def get_daily_intake_for_age(self, standard, age):
        if not standard:
            return 0
        return frappe.db.get_value("Performance Standard Item", {"parent": standard, "day": ["<=", age]}, "daily_feed_intake_grams", order_by="day desc")
