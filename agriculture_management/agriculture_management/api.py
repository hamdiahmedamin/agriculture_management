import frappe


@frappe.whitelist()
def get_farm_map_data(company):
    """
    Fetches a hierarchical structure of the farm layout, now providing
    active/total counts and the parent asset's status, filtered by company.
    """
    if not company:
        frappe.throw(_("A Company must be selected to view the Farm Map."))

    final_map = {}

    # --- PART 1: Fetch Hydroponics Systems ---
    greenhouses = frappe.get_all(
        "Asset",
        filters={
            "asset_category": ["in", ["Greenhouse", "Hydroponic Systems"]],
            "company": company,
            "status": ["!=", "Cancelled"]  # Filter out cancelled systems
        },
        fields=[
            "name", "asset_name", "status",
            "custom_naming_prefix", "custom_number_of_racks",
            "custom_tiers_per_rack", "custom_gullies_per_tier"
        ]
    )
    all_zones = frappe.get_all("Growing Zone", fields=[
                               "name", "zone_name", "status", "current_crop", "hydroponic_system"])

    hydroponics_data = []
    for gh in greenhouses:
        gh_zones = [z for z in all_zones if z.hydroponic_system == gh.name]
        total_zones = len(gh_zones)
        active_zones = sum(1 for z in gh_zones if z.current_crop)

        hydroponics_data.append({
            "doc_type": "Asset", "name": gh.name, "display_name": gh.asset_name,
            "type": "Hydroponic System", "status": gh.status,
            "contents": gh_zones,
            "total_content": total_zones,
            "active_content": active_zones,
            "occupancy_rate": round((active_zones / total_zones) * 100) if total_zones > 0 else 0,
            "layout": {"prefix": gh.custom_naming_prefix, "racks": gh.custom_number_of_racks,
                        "tiers": gh.custom_tiers_per_rack, "gullies": gh.custom_gullies_per_tier}
        })
    final_map['hydroponics'] = hydroponics_data

    # --- PART 2: Fetch Warehouses and Livestock Groups ---
    livestock_parent_wh = frappe.db.get_single_value(
        'Livestock Settings', 'main_livestock_warehouse_group')
    livestock_data = []
    if livestock_parent_wh:
        mid_level_warehouses = frappe.get_all(
            "Warehouse",
            filters={"parent_warehouse": livestock_parent_wh,
                     "is_group": 1, "company": company},
            fields=["name", "warehouse_name"]
        )
        if mid_level_warehouses:
            mid_level_wh_dict = {wh['name']: wh for wh in mid_level_warehouses}
            for wh_name in mid_level_wh_dict:
                mid_level_wh_dict[wh_name]['contents'] = []

            child_warehouses = frappe.get_all("Warehouse", filters={
                                              "is_group": 0, "company": company}, fields=["name", "parent_warehouse"])
            child_to_mid_level_map = {
                c.name: c.parent_warehouse for c in child_warehouses}
            livestock_groups = frappe.get_all(
                "Livestock Group",
                filters={"company": company, "status": "Active"},
                fields=["name", "group_name", "group_location",
                        "species", "total_animals"]
            )

            for group in livestock_groups:
                if group.group_location in child_to_mid_level_map:
                    parent_warehouse_name = child_to_mid_level_map[group.group_location]
                    if parent_warehouse_name in mid_level_wh_dict:
                        mid_level_wh_dict[parent_warehouse_name]['contents'].append(
                            group)

            for wh in mid_level_wh_dict.values():
                total_groups = len(wh['contents'])
                livestock_data.append({
                    "doc_type": "Warehouse", "name": wh['name'], "display_name": wh['warehouse_name'],
                    "type": "Livestock Area", "contents": wh['contents'],
                    "total_content": total_groups,
                    "active_content": total_groups,
                    "occupancy_rate": 100 if total_groups > 0 else 0
                })
    final_map['livestock'] = livestock_data

    return final_map
