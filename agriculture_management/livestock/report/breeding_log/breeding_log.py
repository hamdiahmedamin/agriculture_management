# breeding_log.py
import frappe


def execute(filters=None):
    columns = get_columns()
    data = get_data(filters)
    return columns, data


def get_columns():
    """Defines the columns for the report view."""
    return [
        {"label": "Dam (Mother)", "fieldname": "dam",
         "fieldtype": "Link", "options": "Animal", "width": 150},
        {"label": "Sire (Father)", "fieldname": "sire",
         "fieldtype": "Link", "options": "Animal", "width": 150},
        {"label": "Species", "fieldname": "species", "fieldtype": "Link",
            "options": "Livestock Species", "width": 120},
        {"label": "Breeding Date", "fieldname": "breeding_date",
            "fieldtype": "Date", "width": 130},
        {"label": "Expected Due Date", "fieldname": "expected_due_date",
            "fieldtype": "Date", "width": 150},
        {"label": "Outcome", "fieldname": "outcome",
            "fieldtype": "Data", "width": 120},
        {"label": "Offspring", "fieldname": "offspring",
            "fieldtype": "Link", "options": "Animal", "width": 150},
        {"label": "Actual Birth Date", "fieldname": "birth_date",
            "fieldtype": "Date", "width": 130},
        # This column will be a clickable link to the source Breeding Event
        {"label": "Event ID", "fieldname": "name", "fieldtype": "Link",
            "options": "Breeding Event", "width": 180},
    ]


def get_data(filters):
    """Fetches and filters breeding data from the standalone Breeding Event table."""
    conditions = []
    values = {}

    # Build conditions based on the user's filters
    if filters.get("dam"):
        conditions.append("dam = %(dam)s")
        values["dam"] = filters["dam"]

    if filters.get("sire"):
        conditions.append("sire = %(sire)s")
        values["sire"] = filters["sire"]

    if filters.get("species"):
        conditions.append("species = %(species)s")
        values["species"] = filters["species"]

    if filters.get("outcome"):
        conditions.append("outcome = %(outcome)s")
        values["outcome"] = filters["outcome"]

    if filters.get("date_range"):
        conditions.append(
            "breeding_date BETWEEN %(from_date)s AND %(to_date)s")
        values["from_date"] = filters["date_range"][0]
        values["to_date"] = filters["date_range"][1]

    # Always exclude cancelled documents
    conditions.append("docstatus != 2")

    where_clause = " AND ".join(conditions)

    # The main SQL query now targets the correct 'tabBreeding Event' table.
    query = f"""
        SELECT
            name,
            dam,
            sire,
            species,
            breeding_date,
            expected_due_date,
            outcome,
            offspring,
            birth_date
        FROM
            `tabBreeding Event`
        WHERE
            {where_clause}
        ORDER BY
            breeding_date DESC
    """

    result = frappe.db.sql(query, values, as_dict=1)
    return result
