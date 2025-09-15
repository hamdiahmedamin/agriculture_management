import frappe
from frappe import _


def execute(filters=None):
    # Always have a fallback for filters
    if not filters:
        filters = {}

    # 1. DEFINE COLUMNS
    columns = get_columns()

    # 2. GET DATA
    data = get_data(filters)

    return columns, data


def get_columns():
    """Defines the columns that will be shown in the report view."""
    return [
        {"label": _("ID"), "fieldname": "id", "fieldtype": "Link",
         "options": "Animal", "width": 140},
        {"label": _("Acquisition Cost"), "fieldname": "acquisition_cost",
         "fieldtype": "Currency", "width": 130},
        {"label": _("Feed Cost"), "fieldname": "feed_cost",
         "fieldtype": "Currency", "width": 120},
        {"label": _("Health Cost"), "fieldname": "health_cost",
         "fieldtype": "Currency", "width": 120},
        {"label": _("Gross Expenses"), "fieldname": "gross_expenses",
         "fieldtype": "Currency", "width": 130},
        {"label": _("Product Revenue"), "fieldname": "product_revenue",
         "fieldtype": "Currency", "width": 130},
        {"label": _("Sale Revenue"), "fieldname": "sale_revenue",
         "fieldtype": "Currency", "width": 120},
        {"label": _("Total Revenue"), "fieldname": "total_revenue",
         "fieldtype": "Currency", "width": 120},
        {
            "label": _("Net Profit / Loss"), "fieldname": "net_profit", "fieldtype": "Currency", "width": 140,
            # Add custom cell formatting for profit/loss
            "formatter": lambda val: f"<span style='color:green; font-weight:bold;'>{frappe.format(val, dict(fieldname='net_profit'))}</span>" if val > 0 else f"<span style='color:red; font-weight:bold;'>{frappe.format(val, dict(fieldname='net_profit'))}</span>"
        },
    ]


def get_data(filters):
    """Fetches and processes all the financial data for the report."""

    # Prepare filters
    date_range = filters.get("date_range")
    if not date_range or len(date_range) != 2:
        frappe.throw(_("Date Range is a mandatory filter."))
    from_date, to_date = date_range

    # Get the list of animals to analyze
    animals_to_process = get_animals(filters)
    if not animals_to_process:
        return []

    # Get cost centers for these animals
    cost_centers = get_cost_centers_for_animals(animals_to_process)

    # Fetch all relevant GL entries and Sales Invoices at once for performance
    gl_entries = get_gl_entries(cost_centers.keys(), from_date, to_date)
    product_sales = get_product_sales(cost_centers.keys(), from_date, to_date)

    report_data = []
    for animal in animals_to_process:
        cost_center = cost_centers.get(animal.name)
        if not cost_center:
            continue

        # Calculate expenses
        feed_cost = gl_entries.get(cost_center, {}).get("Animal Feed", 0)
        health_cost = gl_entries.get(
            cost_center, {}).get("Veterinary Medicine", 0)

        # Calculate revenue
        product_revenue = product_sales.get(cost_center, 0)
        sale_revenue, acquisition_cost = get_animal_sale_info(
            animal.name, animal.asset, from_date, to_date)

        # Sum up totals
        gross_expenses = (
            acquisition_cost if not sale_revenue else 0) + feed_cost + health_cost
        total_revenue = product_revenue + sale_revenue
        net_profit = total_revenue - gross_expenses

        report_data.append({
            "id": animal.name,
            "acquisition_cost": acquisition_cost,
            "feed_cost": feed_cost,
            "health_cost": health_cost,
            "gross_expenses": gross_expenses,
            "product_revenue": product_revenue,
            "sale_revenue": sale_revenue,
            "total_revenue": total_revenue,
            "net_profit": net_profit
        })

    return report_data

# --- Helper Functions ---


def get_animals(filters):
    """Returns a list of livestock documents to process based on filters."""
    conditions = ""
    if filters.get("Animal"):
        conditions += f"AND name = '{filters.get('livestock')}'"
    elif filters.get("livestock_group"):
        # This assumes you have a link field 'livestock_group' on the Livestock Doctype
        conditions += f"AND livestock_group = '{filters.get('livestock_group')}'"

    return frappe.get_all("Animal", fields=["name", "asset"], filters=f"docstatus = 1 {conditions}")


def get_cost_centers_for_animals(animals):
    """Creates a mapping of Animal -> Cost Center."""
    # This is an example, you need to adapt it to your structure.
    # Assuming Livestock Group has a cost_center field and Livestock links to Livestock Group
    animal_groups = frappe.get_all("Animal", filters={"name": (
        "in", [d.name for d in animals])}, fields=["name", "livestock_group"])
    group_names = [
        d.livestock_group for d in animal_groups if d.livestock_group]
    group_cost_centers = frappe.get_all("Livestock Group", filters={
                                        "name": ("in", group_names)}, fields=["name", "cost_center"])

    group_map = {d.name: d.cost_center for d in group_cost_centers}
    animal_to_group = {d.name: d.livestock_group for d in animal_groups}

    return {animal_name: group_map.get(group_name) for animal_name, group_name in animal_to_group.items()}


def get_gl_entries(cost_centers, from_date, to_date):
    """Fetch all expense entries from General Ledger, grouped by cost center and account."""
    # This is a simplified query. It assumes a direct link between account and expense type.
    # A more robust solution might check the Item Group from the underlying Stock Entry.
    # For now, we link via standard accounts for 'Feed' and 'Health'.

    # You would configure these account names in Livestock Settings
    feed_account = "Animal Feed - AG"  # Example account name
    health_account = "Veterinary Expenses - AG"  # Example account name

    gle = frappe.db.sql(f"""
        SELECT cost_center, account, SUM(debit) as total_cost
        FROM `tabGL Entry`
        WHERE cost_center IN %(cost_centers)s
        AND posting_date BETWEEN %(from_date)s AND %(to_date)s
        AND account IN %(accounts)s
        GROUP BY cost_center, account
    """, {
        "cost_centers": tuple(cost_centers),
        "from_date": from_date,
        "to_date": to_date,
        "accounts": (feed_account, health_account)
    }, as_dict=1)

    result = {}
    for r in gle:
        result.setdefault(r.cost_center, {})
        expense_type = "Animal Feed" if r.account == feed_account else "Veterinary Medicine"
        result[r.cost_center][expense_type] = r.total_cost
    return result


def get_product_sales(cost_centers, from_date, to_date):
    """Fetch total revenue from product sales (milk, eggs, etc.)"""
    sales = frappe.db.sql("""
        SELECT cost_center, SUM(base_net_amount) as total_sales
        FROM `tabSales Invoice Item`
        WHERE docstatus = 1
        AND parenttype = 'Sales Invoice'
        AND cost_center IN %(cost_centers)s
        AND posting_date BETWEEN %(from_date)s AND %(to_date)s
        GROUP BY cost_center
    """, {"cost_centers": tuple(cost_centers), "from_date": from_date, "to_date": to_date}, as_dict=1)

    return {s.cost_center: s.total_sales for s in sales}


def get_animal_sale_info(livestock_name, asset_name, from_date, to_date):
    """Get acquisition cost from asset and check if it was sold in the date range."""
    acquisition_cost = 0
    if asset_name:
        acquisition_cost = frappe.db.get_value(
            "Asset", asset_name, "gross_purchase_amount") or 0

    # Check for a disposal sale
    sale_revenue = frappe.db.get_value("Sales Invoice Item",
                                       filters={
                                           "asset": asset_name,
                                           "parenttype": "Sales Invoice",
                                           "docstatus": 1,
                                           "posting_date": ["between", [from_date, to_date]]
                                       },
                                       fieldname="base_net_amount"
                                       ) or 0

    return sale_revenue, acquisition_cost
