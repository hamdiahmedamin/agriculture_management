frappe.query_reports["Livestock Profitability Analysis"] = {
    "filters": [
        {
            "fieldname": "date_range",
            "label": __("Date Range"),
            "fieldtype": "DateRange",
            "reqd": 1,
            "default": [frappe.datetime.add_months(frappe.datetime.now_date(), -1), frappe.datetime.now_date()]
        },
        {
            "fieldname": "livestock_group",
            "label": __("Livestock Group"),
            "fieldtype": "Link",
            "options": "Livestock Group"
        },
        {
            "fieldname": "livestock",
            "label": __("Livestock"),
            "fieldtype": "Link",
            "options": "Livestock",
            // This will filter the livestock based on the selected group
            get_query: function() {
                var group = frappe.query_report.get_filter_value('livestock_group');
                if (group) {
                    return {
                        filters: {
                            'livestock_group': group
                        }
                    };
                }
            }
        }
    ]
};