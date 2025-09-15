# Copyright (c) 2025, aminos and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.utils import nowdate, flt, date_diff, getdate
from frappe import _


class PoultryFlock(Document):
    def before_save(self):
        if self.hatch_date:
            self.age_in_days = date_diff(nowdate(), self.hatch_date)
        if self.weight_tracking_history:
            latest_entry = sorted(
                self.weight_tracking_history, key=lambda x: x.date, reverse=True)[0]
            weight = flt(latest_entry.average_weight)
            uom = latest_entry.uom
            self.average_body_weight = weight / 1000 if uom == 'g' else weight
        else:
            self.average_body_weight = 0

    def on_update(self):
        """
        After the flock is saved, run all necessary synchronization hooks.
        """
        self.sync_group_status()

    # --- NEW KPI CALCULATION ENGINE ---
    @frappe.whitelist()
    def recalculate_kpis(self):
        """
        A central function to calculate all major KPIs for the flock.
        """
        # 1. Livability Rate
        if flt(self.initial_head_count) > 0:
            self.livability_rate = (
                flt(self.current_head_count) / flt(self.initial_head_count)) * 100
        else:
            self.livability_rate = 0

        # 2. Costs (These rely on the financial fields being up-to-date)
        total_costs = flt(self.total_feed_cost) + \
            flt(self.total_medication_cost)

        # 3. Cost Per Bird
        if flt(self.initial_head_count) > 0:
            self.cost_per_bird = total_costs / self.initial_head_count
        else:
            self.cost_per_bird = 0

        # 4. Cost Per Dozen Eggs
        if self.flock_type == "Layer" and flt(self.total_eggs_collected) > 0:
            total_dozens = flt(self.total_eggs_collected) / 12
            self.cost_per_dozen_eggs = total_costs / total_dozens
        else:
            self.cost_per_dozen_eggs = 0

        # 5. Feed Conversion Ratio (FCR) for Broilers
        if self.flock_type == "Broiler" and flt(self.total_weight_sold_kg) > 0:
            feed_data = frappe.db.sql("""
                SELECT SUM(sed.qty) FROM `tabStock Entry Detail` sed
                JOIN `tabStock Entry` se ON sed.parent = se.name
                WHERE sed.custom_livestock_group = %s AND se.docstatus = 1 AND sed.item_code != %s
            """, (self.livestock_group, self.item))
            total_feed_kg = flt(
                feed_data[0][0]) if feed_data and feed_data[0][0] else 0

            if total_feed_kg > 0:
                self.fcr = total_feed_kg / self.total_weight_sold_kg
            else:
                self.fcr = 0

        self.save(ignore_permissions=True)
    # --- END OF NEW KPI ENGINE ---

    @frappe.whitelist()
    def update_performance_metrics(self):
        egg_data = frappe.db.sql("""
            SELECT SUM(quantity)
            FROM `tabLivestock Performance Log`
            WHERE poultry_flock = %s AND log_type = 'Egg Collection' AND docstatus = 1
        """, (self.name))
        self.total_eggs_collected = flt(
            egg_data[0][0]) if egg_data and egg_data[0][0] else 0
        self.save(ignore_permissions=True)
        self.recalculate_kpis()  # ADDED TRIGGER

    @frappe.whitelist()
    def update_financial_metrics(self):
        revenue_data = frappe.db.sql("""
            SELECT SUM(dn.grand_total)
            FROM `tabDelivery Note` as dn
            WHERE dn.custom_livestock_group = %s AND dn.docstatus = 1
        """, (self.livestock_group))
        total_revenue = flt(
            revenue_data[0][0]) if revenue_data and revenue_data[0][0] else 0
        self.total_revenue = total_revenue
        total_costs = flt(self.total_feed_cost) + \
            flt(self.total_medication_cost)
        self.gross_profit = self.total_revenue - total_costs
        self.save(ignore_permissions=True)
        self.recalculate_kpis()  # ADDED TRIGGER

    @frappe.whitelist()
    def receive_flock_into_stock(self):
        if self.status != "Planning":
            frappe.throw("This flock has already been received into stock.")
        if not self.initial_head_count or not self.coop or not self.item:
            frappe.throw(
                "Please ensure Item, Coop/Location, and Initial Head Count are set.")
        is_stock_item, valuation_rate = frappe.db.get_value(
            "Item", self.item, ["is_stock_item", "valuation_rate"])
        if not is_stock_item:
            frappe.throw(f"Item '{self.item}' must be a stock item.")
        batch = frappe.get_doc({"doctype": "Batch", "item": self.item,
                               "batch_id": self.name}).insert(ignore_permissions=True)
        self.db_set("batch", batch.name)
        group = frappe.get_doc({
            "doctype": "Livestock Group",
            "group_name": self.name,
            "species": self.specie,
            "group_location": self.coop,
            "main_group_type": "Production",
            "group_type": "Free Range Flock",
            "is_flock": 1
        }).insert(ignore_permissions=True)
        self.db_set("livestock_group", group.name)
        se = frappe.get_doc({
            "doctype": "Stock Entry",
            "stock_entry_type": "Material Receipt", "purpose": "Material Receipt",
            "set_posting_time": 1, "posting_date": self.acquisition_date or nowdate(),
            "use_serial_batch_fields": 1,
            "items": [{
                "item_code": self.item,
                "qty": self.initial_head_count,
                "t_warehouse": self.coop,
                "use_serial_batch_fields": 1,
                "batch_no": batch.name,
                "custom_livestock_group": self.livestock_group}]
        })
        se.insert(ignore_permissions=True)
        se.submit()
        self.db_set("status", "Active")
        self.db_set("current_head_count", self.initial_head_count)
        self.recalculate_kpis()  # ADDED TRIGGER
        return {"se_name": se.name}

    @frappe.whitelist()
    def record_mortality(self, quantity, cause=None):
        if self.status != "Active":
            frappe.throw(_("Can only record mortality for an Active flock."))

        quantity = flt(quantity)
        if quantity <= 0:
            frappe.throw(_("Quantity must be greater than zero."))
        if quantity > self.current_head_count:
            frappe.throw(
                _("Mortality quantity ({0}) cannot exceed current head count ({1}).")
                .format(quantity, self.current_head_count)
            )
        if not self.batch:
            frappe.throw(
                _("Cannot record mortality. The flock is not linked to a Batch."))
        se = frappe.get_doc({
            "doctype": "Stock Entry",
            "stock_entry_type": "Material Issue",
            "purpose": "Material Issue",
            "set_posting_time": 1,
            "posting_date": nowdate(),
            "custom_livestock_group": self.livestock_group,
            "remarks": cause,
            "items": [{
                "item_code": self.item,
                "qty": quantity,
                "s_warehouse": self.coop,
                "use_serial_batch_fields": 1,
                "batch_no": self.batch,
                "custom_livestock_group": self.livestock_group
            }]
        })
        se.insert(ignore_permissions=True)
        se.submit()
        new_head_count = self.current_head_count - quantity
        if new_head_count <= 0:
            self.db_set("current_head_count", 0)
            self.db_set("status", "Deceased")
        else:
            self.db_set("current_head_count", new_head_count)
        self.recalculate_kpis()  # ADDED TRIGGER
        return {"se_name": se.name}

    @frappe.whitelist()
    def record_feeding(self, feed_item, quantity):
        """
        Records a DIRECT feeding event. It creates a Stock Entry with ONLY
        the custom_livestock_group field set.
        """
        if not self.livestock_group:
            frappe.throw("Flock is not linked to a Livestock Group.")
        if not feed_item or flt(quantity) <= 0:
            frappe.throw(
                "Please select a valid Feed Item and a Quantity greater than zero.")

        try:
            group_data = frappe.get_value("Livestock Group", self.livestock_group,
                                          ["group_location", "cost_center"], as_dict=True)
            if not group_data or not group_data.get("group_location"):
                frappe.throw(
                    f"Please set a 'Group Location' for Livestock Group '{self.livestock_group}'.")

            # Create a simple Stock Entry with no schedule link.
            se = frappe.get_doc({
                "doctype": "Stock Entry",
                "stock_entry_type": "Material Issue",
                "purpose": "Material Issue",
                "set_posting_time": 1,
                "posting_date": nowdate(),
                "custom_livestock_group": self.livestock_group,
                "cost_center": group_data.get("cost_center"),
                "items": [{
                    "item_code": feed_item,
                    "qty": flt(quantity),
                    "s_warehouse": group_data.get("group_location"),
                    "cost_center": group_data.get("cost_center"),
                    "custom_livestock_group": self.livestock_group
                }]
            })
            se.insert(ignore_permissions=True)
            se.submit()

            frappe.msgprint(
                _("Direct feeding recorded in Stock Entry <a href='/app/stock-entry/{0}'>{0}</a>").format(se.name), indicator='green')
            return se.name
        except Exception as e:
            frappe.log_error(frappe.get_traceback())
            frappe.throw(f"Failed to create Stock Entry. Error: {e}")

    @frappe.whitelist()
    def sell_flock(self, quantity, customer, selling_rate, total_weight_sold=0):  # SIGNATURE UPDATED
        if self.status != "Active":
            frappe.throw("Can only sell an Active flock.")
        quantity_to_sell = flt(quantity)
        rate_for_dn = flt(selling_rate)
        if quantity_to_sell > self.current_head_count:
            frappe.throw(
                "Quantity to sell cannot exceed the current head count.")
        if rate_for_dn <= 0:
            frappe.throw("The Rate must be a positive number.")
        dn = frappe.get_doc({
            "doctype": "Delivery Note", "customer": customer,
            "custom_livestock_group": self.livestock_group,
            "items": [{"item_code": self.item, "qty": quantity_to_sell, "warehouse": self.coop,
                       "batch_no": self.batch, "rate": rate_for_dn}]
        })
        dn.insert(ignore_permissions=True)
        dn.submit()

        # ADDED: Save weight for FCR calculation
        if self.flock_type == "Broiler":
            self.db_set("total_weight_sold_kg", flt(
                self.total_weight_sold_kg) + flt(total_weight_sold))

        new_head_count = self.current_head_count - quantity_to_sell
        if new_head_count <= 0:
            self.db_set("status", "Sold")
            self.db_set("current_head_count", 0)
        else:
            self.db_set("current_head_count", new_head_count)
        self.recalculate_kpis()  # ADDED TRIGGER
        return {"dn_name": dn.name}

    @frappe.whitelist()
    def administer_medication(self, medication_item, dosage, cost):
        treatment = frappe.get_doc({
            "doctype": "Group Treatment", "livestock_group": self.livestock_group, "date": nowdate(),
            "total_cost": cost,
            "medications_administered": [{"item": medication_item, "dosage": dosage}]
        }).insert(ignore_permissions=True)
        return f"Group Treatment {treatment.name} created."

    @frappe.whitelist()
    def sync_head_count_with_batch(self):
        if not self.batch:
            frappe.throw(_("Cannot sync. The flock is not linked to a Batch."))
        actual_batch_qty = frappe.db.get_value(
            "Batch", self.batch, "batch_qty")
        actual_batch_qty = flt(actual_batch_qty)
        status_changed, original_status = False, self.status
        if actual_batch_qty > 0 and self.status in ["Sold", "Culled", "Deceased"]:
            self.db_set("status", "Active")
            status_changed = True
        elif actual_batch_qty <= 0 and self.status == "Active":
            self.db_set("status", "Sold")
            status_changed = True
        if actual_batch_qty == self.current_head_count and not status_changed:
            frappe.msgprint(
                _("The Head Count and Status are already in sync with the Batch quantity."), indicator='green')
            return True
        old_head_count = self.current_head_count
        self.db_set("current_head_count", actual_batch_qty)
        message_parts = [
            _("Head Count corrected from <b>{0}</b> to <b>{1}</b>.").format(old_head_count, actual_batch_qty)]
        if status_changed:
            new_status = self.db_get("status")
            message_parts.append(
                _("Status updated from <b>{0}</b> to <b>{1}</b>.").format(original_status, new_status))
        frappe.msgprint("<br>".join(message_parts), title=_(
            "Flock Synchronized"), indicator='green')
        self.recalculate_kpis()  # ADDED TRIGGER
        return True

    def sync_group_status(self):
        original_doc = self.get_doc_before_save()
        if not original_doc or self.status == original_doc.status:
            return
        if self.livestock_group:
            try:
                frappe.db.set_value(
                    "Livestock Group", self.livestock_group, "status", self.status)
                frappe.msgprint(_("The status for Livestock Group <b>{0}</b> has been updated to <b>{1}</b>.").format(self.livestock_group, self.status),
                                title=_("Livestock Group Updated"), indicator='green')
            except Exception as e:
                frappe.log_error(
                    f"Could not sync status for Livestock Group {self.livestock_group}. Error: {e}")

    @frappe.whitelist()
    def sell_eggs(self, sales_details):
        """
        Creates a Delivery Note for selling a specific BATCH of eggs.
        This version checks for stock directly on the Batch document.
        """
        flock = frappe.get_doc("Poultry Flock", self.name)
        details = frappe._dict(sales_details)

        if not all([details.customer, details.egg_item, details.batch_no, flt(details.quantity) > 0, flt(details.rate) > 0]):
            frappe.throw(
                _("Customer, Egg Item, Batch, Quantity, and Rate are required."))

        # --- THIS IS THE DEFINITIVE FIX, BASED ON YOUR CORRECT GUIDANCE ---
        # Get the available quantity directly from the 'batch_qty' field of the Batch document.
        # This is correct because your business rule states a batch is only in one warehouse.
        available_qty = frappe.db.get_value(
            "Batch", details.batch_no, "batch_qty")
        available_qty = flt(available_qty)
        # --- END OF FIX ---

        if available_qty < flt(details.quantity):
            frappe.throw(_("Insufficient Stock. Only {0} units of Batch {1} available.")
                         .format(available_qty, details.batch_no))

        # --- DELIVERY NOTE NOW USES THE BATCH ---
        dn = frappe.get_doc({
            "doctype": "Delivery Note",
            "customer": details.customer,
            "posting_date": nowdate(),
            "custom_livestock_group": flock.livestock_group,
            "items": [{
                "item_code": details.egg_item,
                "warehouse": flock.coop,
                "qty": details.quantity,
                "rate": details.rate,
                "use_serial_batch_fields": 1,
                "batch_no": details.batch_no
            }]
        })
        dn.insert(ignore_permissions=True)
        dn.submit()

        frappe.msgprint(
            _("Created Delivery Note <a href='/app/delivery-note/{0}'><b>{0}</b></a> for egg sale from Batch {1}.")
            .format(dn.name, details.batch_no), indicator='green', title="Sale Recorded"
        )
        return True
