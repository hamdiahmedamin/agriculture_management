import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import get_link_to_form, getdate, flt, nowdate


class HarvestLog(Document):
    def before_submit(self):
        self.status = "Pending Stock Entry"
        self.calculate_performance_analytics()
        settings = frappe.get_single("Agriculture Settings")
        if settings.get("qi_mandatory_for_harvest"):
            self.validate_quality_inspections()

    def on_update_after_submit(self):
        self.db_set("status", "Pending Stock Entry")
        self.db_set("generated_stock_entry", None)
        self.db_set("linked_quality_inspection", None)
        for item_row in self.harvested_items:
            item_row.db_set("quality_inspection", None)

    def on_submit(self):
        self.create_stock_entry_from_harvest()
        self.db_set("status", "Completed")

        # --- MERGED LOGIC: ADD SUMMARY TO CROP CYCLE ---
        self.update_crop_cycle_summary(action="add")

    def on_cancel(self):
        # Part 1: Cancel Linked Stock Entry
        if self.generated_stock_entry:
            try:
                stock_entry = frappe.get_doc(
                    "Stock Entry", self.generated_stock_entry)
                if stock_entry.docstatus == 1:
                    stock_entry.cancel()
            except frappe.DoesNotExistError:
                frappe.log_error(
                    f"Linked Stock Entry {self.generated_stock_entry} not found.", "Harvest Log Cancellation")
        self.db_set("generated_stock_entry", None)

        # Part 2: Reset Parent Harvest Entry
        if self.source_harvest_entry:
            try:
                parent_entry = frappe.get_doc(
                    "Harvest Entry", self.source_harvest_entry)
                if parent_entry.status == "Completed":
                    parent_entry.db_set("status", "Draft")
                    frappe.msgprint(
                        _("Source document <strong>{0}</strong> has been unlocked.").format(
                            get_link_to_form(
                                "Harvest Entry", parent_entry.name)
                        ),
                        title=_("Harvest Entry Reset"), indicator="info"
                    )
                for row in parent_entry.zones_harvested:
                    if row.generated_harvest_log == self.name:
                        row.db_set('generated_harvest_log',
                                   None, update_modified=False)
                        break
            except frappe.DoesNotExistError:
                frappe.log_error(
                    f"Parent Harvest Entry {self.source_harvest_entry} not found.", "Harvest Log Cancellation")

        # --- MERGED LOGIC: REMOVE SUMMARY FROM CROP CYCLE ---
        self.update_crop_cycle_summary(action="remove")

        frappe.db.commit()

    # --- NEW HELPER FUNCTION TO MANAGE THE SUMMARY TABLE ---

    def update_crop_cycle_summary(self, action):
        if not self.crop_cycle:
            return
        try:
            parent_cycle = frappe.get_doc("Crop Cycle", self.crop_cycle)
            row_found = next(
                (row for row in parent_cycle.harvest_log if row.harvest_log == self.name), None)

            if action == "add":
                if row_found:
                    row_found.status = "Completed"
                    row_found.total_weight_gross = self.total_weight_gross
                else:
                    parent_cycle.append("harvest_log", {
                        "harvest_log": self.name,
                        "harvest_date": self.harvest_date,
                        "total_weight_gross": self.total_weight_gross,
                        "status": "Completed"
                    })

            elif action == "remove" and row_found:
                parent_cycle.remove(row_found)

            parent_cycle.save(ignore_permissions=True)
        except frappe.DoesNotExistError:
            frappe.log_error(
                f"Parent Crop Cycle {self.crop_cycle} not found.", "Harvest Log Summary Update")

    # --- Your existing robust methods remain below ---

    def calculate_performance_analytics(self):
        if not self.crop_cycle or not self.harvested_items:
            return

        if self.harvested_items:
            self.harvest_date = self.harvested_items[0].harvest_date

        total_value = 0
        for item_row in self.harvested_items:
            item_price = frappe.db.get_value("Item Price", {
                                             "item_code": item_row.item_code, "selling": 1}, "price_list_rate") or 0
            total_value += flt(item_row.quantity) * flt(item_price)
        self.valuation_at_harvest = total_value

        crop_cycle = frappe.get_doc("Crop Cycle", self.crop_cycle)
        if self.harvest_date and crop_cycle.start_date:
            self.days_to_harvest = (
                getdate(self.harvest_date) - getdate(crop_cycle.start_date)).days

        gross_weight = flt(self.total_weight_gross) + flt(self.waste_weight)
        if gross_weight > 0:
            self.waste_percentage = (
                flt(self.waste_weight) / gross_weight) * 100
        else:
            self.waste_percentage = 0

    def validate_quality_inspections(self):
        items_missing_accepted_qi = []
        for item_row in self.harvested_items:
            if not item_row.quality_inspection:
                items_missing_accepted_qi.append(item_row.item_code)
                continue
            try:
                qi_status = frappe.db.get_value(
                    "Quality Inspection", item_row.quality_inspection, "status")
                if qi_status != "Accepted":
                    items_missing_accepted_qi.append(
                        f"{item_row.item_code} (Status: {qi_status})")
            except frappe.DoesNotExistError:
                items_missing_accepted_qi.append(
                    f"{item_row.item_code} (Invalid QI Link)")
        if items_missing_accepted_qi:
            frappe.throw(
                _("Cannot Submit. The following items are missing an 'Accepted' Quality Inspection: {0}")
                .format(frappe.bold(", ".join(items_missing_accepted_qi))),
                title=_("Quality Inspection Required")
            )

    def create_stock_entry_from_harvest(self):
        if self.generated_stock_entry or not self.harvested_items:
            return
        try:
            crop_cycle = frappe.get_doc("Crop Cycle", self.crop_cycle)
            se = frappe.new_doc("Stock Entry")
            se.stock_entry_type = "Material Receipt"
            se.company = self.company
            se.set_posting_date = True
            # Assuming you have a custom field `custom_harvest_log` on Stock Entry for traceability
            se.custom_harvest_log = self.name
            for item_row in self.harvested_items:
                if not item_row.target_warehouse:
                    frappe.throw(
                        _("Please set a Target Warehouse for row {0}.").format(item_row.idx))
                se.append("items", {
                    "item_code": item_row.item_code,
                    "qty": item_row.quantity,
                    "uom": item_row.uom,
                    "t_warehouse": item_row.target_warehouse,
                    "cost_center": crop_cycle.cost_center,
                    "batch_no": item_row.batch
                })
            se.insert(ignore_permissions=True)
            se.submit()
            self.db_set("generated_stock_entry", se.name)
        except Exception as e:
            frappe.log_error(frappe.get_traceback())
            frappe.throw(str(e))
