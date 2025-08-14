from frappe import _

def get_data():
    return [
        {
            "module_name": "Livestock",
            "color": "#A9A9A9",
            "icon": "octicon octicon-repo-forked",
            "type": "module",
            "label": _("Livestock"),
            "items": [
                {
                    "type": "page",
                    "name": "genealogy-tree", # Must match the 'name' in your .json
                    "label": _("Genealogy Tree"),
                    "description": _("View animal family trees.")
                }
            ]
        }
    ]