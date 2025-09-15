import frappe
from collections import defaultdict


@frappe.whitelist()
def get_full_family_tree(root_animal_id):
    """
    Fetches the complete family network (ancestors, descendants, AND partners)
    for a single root animal and formats it for the Vis.js library.
    """
    if not root_animal_id or not frappe.db.exists("Animal", root_animal_id):
        return {}

    # 1. Gather all unique IDs for the entire family network
    ancestor_ids = set()
    _get_ancestors(root_animal_id, ancestor_ids)
    descendant_ids = set()
    _get_descendants(root_animal_id, descendant_ids)
    all_related_ids = {root_animal_id} | ancestor_ids | descendant_ids

    # 2. Add all partners to the list of IDs to fetch
    # This query finds all parents of the animals in our main list.
    # This will naturally include partners that weren't in the direct bloodline.
    all_parents_of_family = frappe.db.sql("""
        SELECT DISTINCT sire_father, dam_mother
        FROM `tabAnimal`
        WHERE name IN %(id_list)s
    """, {"id_list": tuple(all_related_ids)}, as_dict=1)

    for parent_pair in all_parents_of_family:
        if parent_pair.sire_father:
            all_related_ids.add(parent_pair.sire_father)
        if parent_pair.dam_mother:
            all_related_ids.add(parent_pair.dam_mother)

    # 3. Fetch and format the data for this complete network
    return _get_nodes_and_edges_by_id(list(all_related_ids))


def _get_nodes_and_edges_by_id(id_list):
    """
    Helper function: Takes a complete list of IDs and returns the formatted
    nodes and edges required by Vis.js, correctly handling all connections.
    """
    if not id_list:
        return {}

    family_data = frappe.get_all("Animal",
                                 fields=["name", "animal_name", "gender", "breed", "date_of_birth", "health_status",
                                         "current_weight", "location_pen", "sire_father", "dam_mother", "livestock_image"],
                                 filters={"name": ("in", id_list)}
                                 )

    nodes = []
    edges = []
    partnerships = {}
    animal_map = {d.name: d for d in family_data}

    for animal in family_data:
        # Add the animal node
        nodes.append({
            "id": animal.name,
            "label": animal.animal_name or animal.name,
            "shape": "circularImage",
            "image": animal.livestock_image,
            "group": animal.gender,
            "breed": animal.breed,
            "date_of_birth": animal.date_of_birth,
            "health_status": animal.health_status,
            "location_pen": animal.location_pen,
            "current_weight": animal.current_weight,
            "sire_father": animal.sire_father,
            "dam_mother": animal.dam_mother
        })

    # --- THE DEFINITIVE FIX: SEPARATE EDGE CREATION ---
    # Iterate through the collected family data again to build relationships
    for animal in family_data:
        sire = animal.get("sire_father")
        dam = animal.get("dam_mother")

        # Ensure parents are in our collected map before creating links
        if sire in animal_map and dam in animal_map:
            # Create a unique partnership ID
            partnership_id = f"p-{'&'.join(sorted([sire, dam]))}"
            if partnership_id not in partnerships:
                # Add the invisible node for the partnership
                nodes.append(
                    {"id": partnership_id, "shape": "dot", "size": 1, "label": " "})
                # Link the partners TO the partnership node
                edges.append(
                    {"from": sire, "to": partnership_id, "arrows": ""})
                edges.append({"from": dam, "to": partnership_id, "arrows": ""})
                partnerships[partnership_id] = True
            # Link the partnership node TO the child
            edges.append(
                {"from": partnership_id, "to": animal.name, "arrows": "to"})
        elif sire in animal_map:
            # Single parent link
            edges.append({"from": sire, "to": animal.name, "arrows": "to"})
        elif dam in animal_map:
            # Single parent link
            edges.append({"from": dam, "to": animal.name, "arrows": "to"})
    # --- END OF FIX ---

    return {"nodes": nodes, "edges": edges}


# Helper functions for recursion (these are unchanged and correct)
def _get_ancestors(animal_id, ancestor_set):
    if not animal_id or animal_id in ancestor_set:
        return
    parents = frappe.get_value("Animal", animal_id, [
                               "sire_father", "dam_mother"])
    if parents:
        sire, dam = parents
        if sire:
            ancestor_set.add(sire)
            _get_ancestors(sire, ancestor_set)
        if dam:
            ancestor_set.add(dam)
            _get_ancestors(dam, ancestor_set)


def _get_descendants(animal_id, descendant_set):
    children = frappe.db.sql("""
        SELECT name FROM `tabAnimal`
        WHERE status = 'Active' AND (sire_father = %(animal_id)s OR dam_mother = %(animal_id)s)
    """, {"animal_id": animal_id}, pluck=True)
    for child_id in children:
        if child_id not in descendant_set:
            descendant_set.add(child_id)
            _get_descendants(child_id, descendant_set)
