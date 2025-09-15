# animal_health_log.py
import frappe


def execute(filters=None):
    columns = get_columns()
    data = get_data(filters)
    return columns, data


def get_columns():
    """Defines the columns that will be displayed in the report."""
    return [
        {"label": "Event Date", "fieldname": "event_date",
            "fieldtype": "Date", "width": 120},
        {"label": "Animal", "fieldname": "animal",
            "fieldtype": "Link", "options": "Animal", "width": 150},
        {"label": "Event Type", "fieldname": "event_type",
            "fieldtype": "Data", "width": 150},

        # --- NEW COLUMN ADDED HERE ---
        {"label": "Status", "fieldname": "status",
            "fieldtype": "Data", "width": 130},

        {"label": "Details", "fieldname": "details",
            "fieldtype": "Data", "width": 250},
        {"label": "Record ID", "fieldname": "record_name",
            "fieldtype": "Dynamic Link", "options": "record_type", "width": 200},
        {"label": "Record Type", "fieldname": "record_type",
            "fieldtype": "Data", "hidden": 1},
    ]


def get_data(filters):
    """Fetches and combines data from all relevant health DocTypes."""
    values = {}

    # --- Build Date Range Filter ---
    date_filter_clause = ""
    if filters.get("date_range"):
        values["from_date"] = filters["date_range"][0]
        values["to_date"] = filters["date_range"][1]
        date_filter_clause = "AND t1.date BETWEEN %(from_date)s AND %(to_date)s"

    # --- Build Animal and Group Filters ---
    animal_list = []
    if filters.get("animal"):
        animal_list.append(filters.get("animal"))

    if filters.get("livestock_group"):
        group_animals = frappe.get_all(
            "Animal List",
            filters={"parent": filters.get(
                "livestock_group"), "parenttype": "Livestock Group"},
            pluck="animal"
        )
        if group_animals:
            animal_list.extend(group_animals)

    if animal_list:
        values["animal_list"] = list(set(animal_list))

    # --- Query 1: Individual Treatment Records ---
    # <<< FIX: Added t1.status to the SELECT statement
    q1 = f"""
        SELECT
            t1.date_of_treatment as event_date,
            t1.animal as animal,
            'Individual Treatment' as event_type,
            t1.status as status,
            CONCAT('Disease: ', COALESCE(t1.disease, 'N/A')) as details,
            t1.name as record_name,
            'Treatment Record' as record_type
        FROM `tabTreatment Record` t1
        WHERE t1.docstatus = 1
        {date_filter_clause.replace('t1.date', 't1.date_of_treatment')}
        {'AND t1.animal IN %(animal_list)s' if animal_list else ''}
    """

    # --- Query 2: Individual Vaccination Records ---
    # <<< FIX: Added t1.status to the SELECT statement (assuming it exists, otherwise NULL)
    q2 = f"""
        SELECT
            t1.date as event_date,
            t1.animal as animal,
            'Individual Vaccination' as event_type,
            'Completed' as status,
            CONCAT('Vaccine: ', COALESCE(t1.vaccine, 'N/A')) as details,
            t1.name as record_name,
            'Vaccination Record' as record_type
        FROM `tabVaccination Record` t1
        WHERE t1.docstatus = 1
        {date_filter_clause}
        {'AND t1.animal IN %(animal_list)s' if animal_list else ''}
    """

    # --- Query 3: Group Treatments ---
    # <<< FIX: Added t1.status to the SELECT statement
    q3 = f"""
        SELECT
            t1.date as event_date,
            t2.animal as animal,
            'Group Treatment' as event_type,
            t1.status as status,
            CONCAT('Disease: ', COALESCE(t1.disease, 'N/A')) as details,
            t1.name as record_name,
            'Group Treatment' as record_type
        FROM `tabGroup Treatment` t1, `tabAnimal List` t2
        WHERE t1.name = t2.parent AND t2.parenttype = 'Group Treatment' AND t1.docstatus = 1
        {date_filter_clause}
        {'AND t2.animal IN %(animal_list)s' if animal_list else ''}
    """

    # --- Query 4: Group Vaccinations ---
    # <<< FIX: Added t1.status to the SELECT statement
    q4 = f"""
        SELECT
            t1.date as event_date,
            t2.animal as animal,
            'Group Vaccination' as event_type,
            t1.status as status,
            CONCAT('Vaccine: ', COALESCE(t1.vaccine, 'N/A')) as details,
            t1.name as record_name,
            'Group Vaccination' as record_type
        FROM `tabGroup Vaccination` t1, `tabAnimal List` t2
        WHERE t1.name = t2.parent AND t2.parenttype = 'Group Vaccination' AND t1.docstatus = 1
        {date_filter_clause}
        {'AND t2.animal IN %(animal_list)s' if animal_list else ''}
    """

    # Combine all queries
    final_query = f"""
        ({q1})
        UNION ALL
        ({q2})
        UNION ALL
        ({q3})
        UNION ALL
        ({q4})
        ORDER BY event_date DESC
    """

    result = frappe.db.sql(final_query, values, as_dict=1)
    return result
