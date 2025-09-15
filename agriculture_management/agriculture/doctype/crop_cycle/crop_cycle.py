import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import add_days, getdate, nowdate, flt


class CropCycle(Document):
    def validate(self):
        """
        Runs before saving. Sets defaults and auto-creates a Cost Center.
        """
        # --- Auto-create Cost Center (CRUCIAL for financials) ---
        if self.is_new() and not self.cost_center:
            company = self.company or frappe.get_cached_value(
                'Company', frappe.defaults.get_user_default('Company'), 'name')
            if not company:
                frappe.throw(
                    _("Please set a default Company for your user or specify one in the Crop Cycle."))

            cost_center_name = f"{self.title} - {self.name}"

            # This checks if a CC with that name and company already exists
            existing_cc = frappe.db.exists(
                "Cost Center", {"cost_center_name": cost_center_name, "company": company})

            if not existing_cc:
                # --- Path 1: The Cost Center does NOT exist. Create it. ---
                parent_cc_name = frappe.db.get_single_value(
                    'Agriculture Settings', 'default_parent_cost_center')
                if not parent_cc_name:
                    frappe.throw(
                        _("Please set the 'Default Parent Cost Center' in Agriculture Settings."))

                if not frappe.db.exists("Cost Center", {"name": parent_cc_name, "company": company}):
                    frappe.throw(
                        _("The Default Parent Cost Center '{0}' set in Agriculture Settings either does not exist or does not belong to the company '{1}'.")
                        .format(parent_cc_name, company)
                    )

                new_cc_doc = frappe.get_doc({
                    "doctype": "Cost Center",
                    "cost_center_name": cost_center_name,
                    "company": company,
                    "is_group": 0,
                    "parent_cost_center": parent_cc_name
                })
                new_cc_doc.insert(ignore_permissions=True)
                self.cost_center = new_cc_doc.name

            else:
                # --- Path 2: The Cost Center ALREADY exists. Find and link to it. ---
                # The 'else' is now correctly paired with 'if not existing_cc:'
                # 'existing_cc' will contain the unique name (e.g., "My CC - FC")
                self.cost_center = existing_cc

        # --- Set missing values from Crop master ---
        if self.crop:
            crop = frappe.get_doc('Crop', self.crop)
            if not self.crop_spacing:
                self.crop_spacing = crop.crop_spacing
            if not self.row_spacing:
                self.row_spacing = crop.row_spacing
            if not self.crop_spacing_uom:
                self.crop_spacing_uom = crop.crop_spacing_uom
            if not self.row_spacing_uom:
                self.row_spacing_uom = crop.row_spacing_uom

    def after_insert(self):
        """
        Runs only when the document is first created and saved.
        """
        self.create_project_and_tasks()

    def create_project_and_tasks(self):
        """
        Creates a Project and links the standard tasks from the Crop master.
        """
        if not self.project and self.crop:
            crop = frappe.get_doc('Crop', self.crop)

            # Create a Project
            project_doc = frappe.get_doc({
                "doctype": "Project",
                "project_name": self.title,
                "expected_start_date": self.start_date,
                "expected_end_date": add_days(self.start_date, crop.get("period", 90) - 1)
            }).insert(ignore_permissions=True)

            self.db_set("project", project_doc.name)
            frappe.msgprint(_("Project {0} created for this Crop Cycle.").format(
                frappe.bold(project_doc.name)))

            # Create standard tasks associated with the crop
            if crop.get("agriculture_task"):
                for crop_task in crop.agriculture_task:
                    frappe.get_doc({
                        "doctype": "Task",
                        "subject": crop_task.get("task_name"),
                        "project": project_doc.name,
                        "exp_start_date": add_days(self.start_date, crop_task.get("start_day", 1) - 1),
                        "exp_end_date": add_days(self.start_date, crop_task.get("end_day", 1) - 1)
                    }).insert(ignore_permissions=True)

    def on_update(self):
        self.unlink_removed_growing_zones()
        """
        After save, update the dashboard of all linked Growing Zones.
        """
        self.update_growing_zone_dashboards()

    def on_cancel(self):
        """
        When cancelled, clear the dashboard of all linked Growing Zones.
        """
        self.update_growing_zone_dashboards(clear=True)

    def update_growing_zone_dashboards(self, clear=False):
        if self.growth_method != "Hydroponic" or not self.growing_zones:
            return

        for zone_link in self.growing_zones:
            if not zone_link.growing_zone:
                continue

            try:
                zone_doc = frappe.get_doc(
                    "Growing Zone", zone_link.growing_zone)

                if clear or self.status in ["Completed", "Cancelled"]:
                    zone_doc.current_crop_cycle = None
                    zone_doc.current_crop = None
                    zone_doc.date_planted = None
                    zone_doc.days_in_cycle = 0
                    zone_doc.occupancy = 0
                elif self.status in ["Started", "In-Progress"]:
                    zone_doc.current_crop_cycle = self.name
                    zone_doc.current_crop = self.crop
                    zone_doc.date_planted = self.start_date

                    if self.start_date:
                        days = (getdate(nowdate()) -
                                getdate(self.start_date)).days
                        zone_doc.days_in_cycle = days if days >= 0 else 0
                    else:
                        zone_doc.days_in_cycle = 0

                    zone_doc.occupancy = 100.0 if zone_doc.plant_capacity > 0 else 0

                zone_doc.save(ignore_permissions=True)

            except frappe.DoesNotExistError:
                frappe.log_error(
                    f"Growing Zone {zone_link.growing_zone} not found.", "Crop Cycle Dashboard Update")

        frappe.db.commit()

    def unlink_removed_growing_zones(self):
        """
        Compares the current list of growing zones in the child table with the list of zones
        that were previously linked to this crop cycle, and unlinks any that were removed.
        """
        # Get the new list of zones from the child table in the document being saved.
        # The .get("growing_zones") method gets the child table data.
        new_zones_in_table = {
            row.growing_zone for row in self.get("growing_zones")}

        # Get the old list of zones that were linked to this Crop Cycle before this save operation.
        # We query the Growing Zone doctype for this.
        old_linked_zones_docs = frappe.get_all(
            "Growing Zone",
            filters={"current_crop_cycle": self.name},
            fields=["name"]
        )
        old_linked_zones = {doc.name for doc in old_linked_zones_docs}

        # Find the zones that need to be unlinked.
        # These are zones that were in the old list but are NOT in the new list.
        zones_to_unlink = old_linked_zones - new_zones_in_table

        if not zones_to_unlink:
            return  # Nothing to do

        # For each zone that was removed from the table, clear its link.
        for zone_name in zones_to_unlink:
            try:
                # Use frappe.db.set_value for a direct, efficient database update.
                # This is better than loading the whole doc just to change one field.
                frappe.db.set_value("Growing Zone", zone_name,
                                    "current_crop_cycle", None)

                # Also clear the other calculated fields in the Growing Zone
                frappe.db.set_value("Growing Zone", zone_name, {
                    "current_crop_cycle": None,
                    "current_crop": None,
                    "date_planted": None,
                    "days_in_cycle": 0,
                    "occupancy": 0,
                    "expected_harvest_date": None
                })

            except frappe.DoesNotExistError:
                # The zone might have been deleted in the meantime, so we can ignore it.
                pass

        frappe.msgprint(
            _("Unlinked {0} Growing Zones that were removed from this Crop Cycle.").format(
                len(zones_to_unlink)),
            indicator="blue"
        )

# --- Whitelisted methods for client-side calls ---


@frappe.whitelist()
def update_dashboard_totals(self):
    """
    Calculates and updates the dashboard fields.
    This definitive version correctly sums data from the 'harvest_log' child table.
    """
    # ... (The rest of this function remains unchanged) ...
    if not self.cost_center:
        frappe.msgprint(
            _("Please set a Cost Center to calculate expenses."))
        self.total_expenses = 0
        self.save()
        return

    # --- 1. Calculate Total Expenses (This part is correct) ---
    total_expenses = frappe.db.get_value("GL Entry",
                                         {"cost_center": self.cost_center, "posting_date": [
                                             "between", (self.start_date, self.end_date or nowdate())]},
                                         "sum(debit) - sum(credit)"
                                         ) or 0

    # --- 2. THIS IS THE CORRECTED LOGIC for Yield and Value ---
    total_yield_kg = 0
    total_waste = 0
    total_value = 0
    last_harvest_date = None

    if self.harvest_log:
        harvest_log_names = [
            h.harvest_log for h in self.harvest_log if h.harvest_log]

        if harvest_log_names:
            harvest_data = frappe.get_all("Harvest Log",
                                          filters={
                                              "name": ("in", harvest_log_names),
                                              "docstatus": 1
                                          },
                                          fields=["name", "total_weight_gross",
                                                  "waste_weight", "valuation_at_harvest"]
                                          )
            harvest_map = {h.name: h for h in harvest_data}
            for summary_row in self.harvest_log:
                log_data = harvest_map.get(summary_row.harvest_log)
                if log_data:
                    total_yield_kg += flt(log_data.total_weight_gross)
                    total_waste += flt(log_data.waste_weight)
                    total_value += flt(log_data.valuation_at_harvest)

                if summary_row.harvest_date:
                    if not last_harvest_date or getdate(summary_row.harvest_date) > last_harvest_date:
                        last_harvest_date = getdate(
                            summary_row.harvest_date)

    # --- 3. Set the final values (This part is now correct) ---
    self.total_expenses = total_expenses
    self.total_yield_kg = total_yield_kg
    self.valuation_at_harvest = total_value

    if total_yield_kg > 0:
        self.expense_per_kg = total_expenses / total_yield_kg
    else:
        self.expense_per_kg = 0

    if self.start_date and last_harvest_date:
        self.days_to_harvest = (
            last_harvest_date - getdate(self.start_date)).days

    gross_weight = total_yield_kg + total_waste
    if gross_weight > 0:
        self.waste_percentage = (total_waste / gross_weight) * 100
    else:
        self.waste_percentage = 0

    self.save(ignore_permissions=True)
    return "Dashboard Updated"


@frappe.whitelist()
def reload_linked_analysis(self):
    """
    Clears and re-populates the analysis child tables with all documents
    that are linked to this Crop Cycle.
    """
    # ... (The rest of this function remains unchanged) ...
    self.set("water_analysis", [])
    linked_water_analyses = frappe.get_all(
        "Water Analysis", filters={"crop_cycle": self.name}, fields=["name"])
    for analysis in linked_water_analyses:
        self.append("water_analysis", {"water_analysis": analysis.name})

    self.set("soil_analysis", [])
    linked_soil_analyses = frappe.get_all(
        "Soil Analysis", filters={"crop_cycle": self.name}, fields=["name"])
    for analysis in linked_soil_analyses:
        self.append("soil_analysis", {"soil_analysis": analysis.name})

    self.set("plant_analysis", [])
    linked_plant_analyses = frappe.get_all(
        "Plant Analysis", filters={"crop_cycle": self.name}, fields=["name"])
    for analysis in linked_plant_analyses:
        self.append("plant_analysis", {"plant_analysis": analysis.name})

    self.set("soil_texture", [])
    linked_soil_textures = frappe.get_all(
        "Soil Texture", filters={"crop_cycle": self.name}, fields=["name"])
    for texture in linked_soil_textures:
        self.append("soil_texture", {"soil_texture": texture.name})

    self.save(ignore_permissions=True)
    frappe.msgprint(
        _("Linked analysis tables have been successfully reloaded."), indicator="green")


@frappe.whitelist()
def reload_harvest_summary(self):
    """
    Wipes and re-populates the 'harvest_log' child table by finding all
    submitted Harvest Logs linked to this Crop Cycle in the database.
    This acts as a manual synchronization tool.
    """
    # --- Step 1: Wipe the existing child table ---
    # This prevents duplicates and ensures the table is a perfect reflection of the database.
    self.set("harvest_log", [])

    # --- Step 2: Find all submitted Harvest Logs linked to this Crop Cycle ---
    linked_harvests = frappe.get_all(
        "Harvest Log",
        filters={
            "crop_cycle": self.name,
            "docstatus": 1  # Crucially, only fetch SUBMITTED logs
        },
        fields=["name as harvest_log", "harvest_date",
                "total_weight_gross", "status"]
    )

    # --- Step 3: Loop through the results and re-populate the table ---
    if linked_harvests:
        for log in linked_harvests:
            self.append("harvest_log", log)

    # --- Step 4: Save the changes to the document ---
    self.save(ignore_permissions=True)

    # --- Step 5: Inform the user ---
    frappe.msgprint(
        _("Harvest summary has been successfully reloaded. {0} logs found.").format(
            len(linked_harvests)),
        indicator="green"
    )
