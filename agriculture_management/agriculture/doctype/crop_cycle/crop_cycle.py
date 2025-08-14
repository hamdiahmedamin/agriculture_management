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
            company = self.company or frappe.get_cached_value('Company', frappe.defaults.get_user_default('Company'), 'name')
            if not company:
                frappe.throw(_("Please set a default Company for your user or specify one in the Crop Cycle."))
            
            cost_center_name = f"{self.title} - {self.name}"
            # Check if Cost Center already exists
            if not frappe.db.exists("Cost Center", cost_center_name):
                # Ensure you have a root Cost Center for your company, e.g., "Main - [Company Abbr]"
                # and a child named "Agriculture". Adjust if your Chart of Accounts is different.
                root_cost_center = frappe.db.get_value("Cost Center", {"is_group": 1, "company": company})
                parent_cost_center = frappe.db.get_value("Cost Center", {"parent_cost_center": root_cost_center, "cost_center_name": "Agriculture"})
                
                if not parent_cost_center:
                     parent_cost_center = root_cost_center # Fallback to root if "Agriculture" doesn't exist

                frappe.get_doc({
                    "doctype": "Cost Center",
                    "cost_center_name": cost_center_name,
                    "company": company,
                    "is_group": 0,
                    "parent_cost_center": parent_cost_center
                }).insert(ignore_permissions=True)
            self.cost_center = cost_center_name

        # --- Set missing values from Crop master ---
        if self.crop:
            crop = frappe.get_doc('Crop', self.crop)
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
            frappe.msgprint(_("Project {0} created for this Crop Cycle.").format(frappe.bold(project_doc.name)))
            
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

    # --- Whitelisted methods for client-side calls ---

    @frappe.whitelist()
    def update_dashboard_totals(self):
        """
        Calculates and updates the dashboard fields.
        This version correctly sums data from all linked Harvest Log documents.
        """
        if not self.cost_center:
            frappe.msgprint(_("Please set a Cost Center to calculate expenses."))
            return

        # --- This part is unchanged ---
        total_expenses = frappe.db.get_value("GL Entry", 
            {"cost_center": self.cost_center, "posting_date": ["<=", self.end_date or nowdate()]}, 
            "sum(debit) - sum(credit)"
        ) or 0
        
        # --- THIS IS THE MODIFIED LOGIC ---
        # Query all completed Harvest Log documents linked to this Crop Cycle
        linked_harvests = frappe.get_all("Harvest Log",
            filters={
                "crop_cycle": self.name,
                "docstatus": 1 # Only count submitted/completed harvests
            },
            fields=["total_weight_gross", "waste_weight", "valuation_at_harvest", "name", "harvest_date"]
        )

        total_yield_kg = sum(flt(h.total_weight_gross) for h in linked_harvests)
        total_waste = sum(flt(h.waste_weight) for h in linked_harvests)
        total_value = sum(flt(h.valuation_at_harvest) for h in linked_harvests)
        # --- END OF MODIFICATION ---

        self.total_expenses = total_expenses
        self.total_yield_kg = total_yield_kg
        self.valuation_at_harvest = total_value
        
        if total_yield_kg > 0:
            self.expense_per_kg = total_expenses / total_yield_kg
        else:
            self.expense_per_kg = 0

        if self.start_date and linked_harvests:
            last_harvest_date = max([getdate(h.harvest_date) for h in linked_harvests if h.harvest_date], default=getdate(self.start_date))
            self.days_to_harvest = (last_harvest_date - getdate(self.start_date)).days
        
        gross_weight = total_yield_kg + total_waste
        if gross_weight > 0:
            self.waste_percentage = (total_waste / gross_weight) * 100
        else:
            self.waste_percentage = 0
        
        self.save(ignore_permissions=True)
        return "Dashboard Updated"