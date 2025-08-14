import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt, getdate


class HarvestLog(Document):
    def before_submit(self):
        self.status = "Pending Stock Entry"
        self.calculate_performance_analytics()

        # Check the global setting to decide if QI validation is needed
        settings = frappe.get_doc("Agriculture Settings")
        if settings.qi_mandatory_for_harvest:
            self.validate_quality_inspections()

    def on_update_after_submit(self):
        """
        This hook runs after a document is amended.
        We need to reset the status and clear fields that should not be copied.
        """
        # When a document is amended, Frappe creates a new draft (docstatus=0)
        # but copies the old values. We must reset the workflow state.
        
        # You should have a default status for new drafts, let's assume it's "Draft"
        # or "Pending Stock Entry". Let's check your workflow.
        # Based on your previous scripts, "Pending Stock Entry" is a good default.
        self.db_set("status", "Pending Stock Entry")

        # It's also good practice to clear fields that are specific to the old transaction
        self.db_set("generated_stock_entry", None)
        self.db_set("linked_quality_inspection", None)
        
        # We also need to clear the QI link from the child table rows
        # as the new amended harvest will need new inspections.
        for item_row in self.harvested_items:
            item_row.db_set("quality_inspection", None)

    def on_submit(self):
        self.create_stock_entry_from_harvest()
        self.db_set("status", "Completed")

    def on_cancel(self):
        self.status = "Cancelled"
        if self.generated_stock_entry:
            try:
                se = frappe.get_doc("Stock Entry", self.generated_stock_entry)
                if se.docstatus == 1:
                    se.cancel()
            except frappe.DoesNotExistError:
                pass
        self.db_set("generated_stock_entry", None)

    def calculate_performance_analytics(self):
        """
        Calculates KPIs for this specific harvest event.
        """
        if not self.crop_cycle or not self.harvested_items:
            return
            
        # --- THIS IS THE DEFINITIVE FIX ---
        # 1. Get the harvest_date from the first row of the child table.
        # This assumes all items in a single log are harvested on the same date.
        harvest_date_from_child = self.harvested_items[0].harvest_date
        
        # 2. Set this date on the parent document so it can be used and saved.
        # This requires you to add a 'harvest_date' field to the Harvest Log DocType.
        self.harvest_date = harvest_date_from_child
        # --- END OF FIX ---

        total_value = 0
        for item_row in self.harvested_items:
            item_price = frappe.db.get_value("Item Price", {
                                             "item_code": item_row.item_code, "selling": 1}, "price_list_rate") or 0
            total_value += flt(item_row.quantity) * flt(item_price)
        self.valuation_at_harvest = total_value

        crop_cycle = frappe.get_doc("Crop Cycle", self.crop_cycle)
        
        # This 'if' condition will now work correctly.
        if self.harvest_date and crop_cycle.start_date:
            self.days_to_harvest = (
                getdate(self.harvest_date) - getdate(crop_cycle.start_date)).days

        if flt(self.total_weight_gross) > 0:
            self.waste_percentage = (
                flt(self.waste_weight) / flt(self.total_weight_gross)) * 100
        else:
            self.waste_percentage = 0

    def validate_quality_inspections(self):
        """
        Checks that EVERY item in the harvest_items table has its own
        'Accepted' Quality Inspection linked to it.
        """
        # Create a list of items that are missing a valid QI
        items_missing_accepted_qi = []

        for item_row in self.harvested_items:
            # Check if the 'quality_inspection' field on the row is empty
            if not item_row.quality_inspection:
                items_missing_accepted_qi.append(item_row.item_code)
                continue # Move to the next item

            # If it's not empty, check the status of the linked QI
            try:
                qi_status = frappe.db.get_value("Quality Inspection", item_row.quality_inspection, "status")
                if qi_status != "Accepted":
                    items_missing_accepted_qi.append(f"{item_row.item_code} (Status: {qi_status})")
            except frappe.DoesNotExistError:
                # This case handles if the QI link is broken for some reason
                items_missing_accepted_qi.append(f"{item_row.item_code} (Invalid QI Link)")

        if items_missing_accepted_qi:
            frappe.throw(
                _("Cannot Submit. The following items are missing an 'Accepted' Quality Inspection: {0}")
                .format(frappe.bold(", ".join(items_missing_accepted_qi))),
                title=_("Quality Inspection Required")
            )
            

    def create_stock_entry_from_harvest(self):
        """
        Creates a single Stock Entry (Material Receipt) for this harvest.
        """
        if self.generated_stock_entry:
            return
        if not self.harvested_items:
            return

        try:
            crop_cycle = frappe.get_doc("Crop Cycle", self.crop_cycle)
            se = frappe.new_doc("Stock Entry")
            se.stock_entry_type = "Material Receipt"
            se.company = self.company
            se.set_posting_date = True
            se.custom_harvest_log = self.name

            for item_row in self.harvested_items:
                # --- THIS IS THE DEFINITIVE FIX ---
                # The Target Warehouse must be specified for each item.
                # We get it from the child table row (item_row).
                if not item_row.target_warehouse:
                    frappe.throw(_("Please set a Target Warehouse for row {0} in the Harvested Items table.").format(item_row.idx))
                
                se.append("items", {
                    "item_code": item_row.item_code,
                    "qty": item_row.quantity,
                    "uom": item_row.uom,
                    "t_warehouse": item_row.target_warehouse, # Get the warehouse from the item row
                    "cost_center": crop_cycle.cost_center,
                    "batch_no": item_row.batch
                })
                # --- END OF FIX ---
            
            se.insert(ignore_permissions=True)
            se.submit()
            self.db_set("generated_stock_entry", se.name)
        except Exception as e:
            frappe.log_error(frappe.get_traceback())
            frappe.throw(str(e))

