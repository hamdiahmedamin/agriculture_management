# Copyright (c) 2025, aminos and contributors
# For license information, please see license.txt

import frappe
from frappe.utils import getdate, today


def execute(filters=None):
    columns = get_columns()
    data = get_data(filters)
    return columns, data


def get_columns():
    return [
        {"label": "Task / Log", "fieldname": "task_log",
            "fieldtype": "Dynamic Link", "options": "task_doctype", "width": 200},
        {"label": "System / Equipment", "fieldname": "hydroponic_system",
            "fieldtype": "Link", "options": "Asset", "width": 180},
        {"label": "Task Type", "fieldname": "task_type",
            "fieldtype": "Data", "width": 250},
        {"label": "Scheduled Date", "fieldname": "scheduled_date",
            "fieldtype": "Date", "width": 140},
        {"label": "Completed Date", "fieldname": "completed_date",
            "fieldtype": "Date", "width": 140},
        {"label": "Status", "fieldname": "status",
            "fieldtype": "Data", "width": 120},
        {"label": "DocType", "fieldname": "task_doctype", "hidden": 1},
    ]


def get_data(filters):
    report_data = []

    # --- Block 1: Planned Tasks (This block is now 100% correct) ---
    planned_tasks = frappe.db.sql("""
        SELECT
            parent.name AS system_name,
            parent.linked_asset AS hydroponic_system,
            child.name AS task_name,
            child.next_replacement_date
        FROM
            `tabFilter Replacement Schedule` AS child
        JOIN
            `tabFiltration System` AS parent ON child.parent = parent.name
        WHERE
            -- This is the correct logic: Find tasks that are not yet marked as 'Replaced'.
            child.is_replaced = 0
            AND child.next_replacement_date IS NOT NULL
    """, as_dict=True)

    for task in planned_tasks:
        status = "Overdue" if getdate(
            task.next_replacement_date) < getdate(today()) else "Upcoming"
        report_data.append({
            "task_log": task.system_name,
            "hydroponic_system": task.hydroponic_system,
            "task_type": "Planned: Filter Change",
            "scheduled_date": task.next_replacement_date,
            "completed_date": None,
            "status": status,
            "task_doctype": "Filtration System"
        })

    # --- Block 2: Completed Sanitization (This part is correct) ---
    sanitization_logs = frappe.get_all("Sanitization Log", fields=[
                                       "name", "hydroponic_system", "sanitization_date"], filters={"docstatus": 1})
    for log in sanitization_logs:
        report_data.append({
            "task_log": log.name,
            "hydroponic_system": log.hydroponic_system,
            "task_type": "Completed: Sanitization",
            "scheduled_date": log.sanitization_date,
            "completed_date": log.sanitization_date,
            "status": "Completed",
            "task_doctype": "Sanitization Log"
        })

    # --- Block 3: Corrective Actions (This part is correct) ---
    corrective_actions = frappe.db.sql("""
        SELECT
            parent.name as wql_name, parent.hydroponic_system, parent.log_timestamp, child.action_type
        FROM `tabCorrective Action` AS child
        JOIN `tabWater Quality Log` AS parent ON child.parent = parent.name
        WHERE parent.docstatus = 1 AND child.action_type IS NOT NULL AND child.action_type != ''
    """, as_dict=True)

    for action in corrective_actions:
        report_data.append({
            "task_log": action.wql_name, "hydroponic_system": action.hydroponic_system,
            "task_type": f"Corrective: {action.action_type}", "scheduled_date": None,
            "completed_date": getdate(action.log_timestamp), "status": "Completed",
            "task_doctype": "Water Quality Log"
        })

    # --- Block 4: Filtering (This part is correct) ---
    final_data = []
    for row in report_data:
        # ... (your existing final filtering logic is correct and remains here) ...
        in_date_range, matches_system, matches_status = True, True, True
        if filters.get("date_range"):
            start_date, end_date = filters["date_range"]
            check_date = row.get("completed_date") or row.get("scheduled_date")
            if not (check_date and getdate(start_date) <= getdate(check_date) <= getdate(end_date)):
                in_date_range = False
        if filters.get("hydroponic_system") and row.get("hydroponic_system") != filters.get("hydroponic_system"):
            matches_system = False
        if filters.get("status") and row.get("status") != filters.get("status"):
            matches_status = False
        if in_date_range and matches_system and matches_status:
            final_data.append(row)

    return final_data
