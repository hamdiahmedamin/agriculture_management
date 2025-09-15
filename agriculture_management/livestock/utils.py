# Copyright (c) 2025, aminos and contributors
# For license information, please see license.txt

import frappe
from frappe.utils import flt
from frappe import _


def update_flock_on_dn_cancel(doc, method):
    """
    This function is triggered by the 'on_cancel' hook for Delivery Note.
    It finds the related Poultry Flock and reverts the head count.

    Args:
        doc (Document): The Delivery Note document being cancelled.
        method (str): The hook method being called (e.g., 'on_cancel').
    """
    # 1. Check if this Delivery Note is linked to a livestock group.
    if not doc.custom_livestock_group:
        return

    # 2. Find the corresponding Poultry Flock.
    try:
        flock_name = frappe.db.get_value(
            "Poultry Flock", {"livestock_group": doc.custom_livestock_group}, "name")
        if not flock_name:
            # The group exists but it's not for a poultry flock, so we do nothing.
            return

        flock_doc = frappe.get_doc("Poultry Flock", flock_name)
    except Exception:
        # If the flock can't be found for any reason, log it and exit gracefully.
        frappe.log_error(
            f"Could not find Poultry Flock for Livestock Group {doc.custom_livestock_group} during DN cancel.")
        return

    # 3. Calculate the new head count by adding the quantity back.
    quantity_to_return = flt(doc.total_qty)
    new_head_count = flt(flock_doc.current_head_count) + quantity_to_return

    # 4. Update the flock document.
    flock_doc.db_set("current_head_count", new_head_count)

    # 5. If the flock was marked as "Sold", revert its status to "Active".
    if flock_doc.status == "Sold":
        flock_doc.db_set("status", "Active")

    # 6. Inform the user.
    frappe.msgprint(
        _("The head count for <b>{0}</b> has been restored by {1} due to the cancellation of this Delivery Note.").format(
            flock_name, quantity_to_return),
        title=_("Poultry Flock Updated"),
        indicator='green'
    )


def validate_delivery_of_livestock(doc, method):
    """
    Called from Delivery Note's 'validate' hook.
    Prevents the sale of any animal currently in a withdrawal period.
    """
    # Get a list of all unique serialized items in the Delivery Note
    serialized_items = {item.serial_no for item in doc.items if item.serial_no}
    if not serialized_items:
        return

    # Find if any of these serial numbers correspond to an animal in a withdrawal period
    violating_animals = frappe.get_all("Animal",
                                       filters={
                                           "serial_no": ["in", list(serialized_items)],
                                           "in_withdrawal_until": [">=", frappe.utils.nowdate()]
                                       },
                                       fields=["name", "in_withdrawal_until"]
                                       )

    if violating_animals:
        error_msg = _(
            "Cannot submit this Delivery Note. The following animals are still in a medication withdrawal period:")
        error_msg += "<ul>"
        for animal in violating_animals:
            error_msg += f"<li><b>{animal.name}</b> (In withdrawal until: {animal.in_withdrawal_until})</li>"
        error_msg += "</ul>"

        frappe.throw(error_msg, title="Withdrawal Period Active")


def check_and_update_withdrawal_status():
    """
    This is a daily scheduled job. It finds all animals whose withdrawal
    period has ended and sets their status back to 'Active'.
    """
    animals_to_release = frappe.get_all("Animal",
                                        filters={
                                            "status": "In Withdrawal",
                                            "in_withdrawal_until": ["<", frappe.utils.nowdate()]
                                        },
                                        pluck="name"
                                        )

    if not animals_to_release:
        return

    for animal_name in animals_to_release:
        try:
            # We use get_doc and save to trigger any other logic on the Animal doctype
            animal = frappe.get_doc("Animal", animal_name)
            animal.status = "Active"
            # It's also good practice to clear the date field
            animal.in_withdrawal_until = None
            animal.save(ignore_permissions=True)
        except Exception:
            frappe.log_error(
                f"Failed to auto-update withdrawal status for Animal {animal_name}")

    frappe.db.commit()
    print(
        f"Released {len(animals_to_release)} animals from withdrawal period.")


def revert_feeding_on_se_cancel(doc, method):
    """
    This function is triggered by the 'on_cancel' hook for Stock Entry.
    It finds related feeding records and reverts them.

    Args:
        doc (Document): The Stock Entry document being cancelled.
        method (str): The hook method being called (e.g., 'on_cancel').
    """
    # 1. Check if this is a feeding-related Stock Entry.
    if doc.purpose != "Material Issue" or not doc.custom_livestock_group:
        return

    # 2. Determine if it was a scheduled or direct feed.
    if doc.custom_feeding_schedule:
        # --- IT WAS A SCHEDULED FEED ---
        try:
            schedule = frappe.get_doc(
                "Feeding Schedule", doc.custom_feeding_schedule)

            # Find the specific row in the log linked to this Stock Entry
            row_to_revert = None
            for log_row in schedule.feeding_schedule_log:
                if log_row.stock_entry == doc.name:
                    row_to_revert = log_row
                    break

            if row_to_revert:
                row_to_revert.status = "Planned"
                row_to_revert.stock_entry = None
                schedule.update_overall_status()  # Recalculate parent status
                schedule.save(ignore_permissions=True)

                frappe.msgprint(
                    _("The status of the corresponding row in Feeding Schedule <strong>{0}</strong> has been reset to 'Planned'.")
                    .format(schedule.name)
                )
        except frappe.DoesNotExistError:
            frappe.log_error(
                f"Could not find Feeding Schedule {doc.custom_feeding_schedule} to revert on SE cancel.")

    else:
        # --- IT WAS A DIRECT FEED ---
        # Direct feeds are only for individual animal groups.
        group = frappe.get_doc("Livestock Group", doc.custom_livestock_group)
        if not group.is_flock and group.animal_list:

            animals_updated = 0
            # We need to find and remove the log entry from each animal.
            for animal_member in group.animal_list:
                animal_doc = frappe.get_doc("Animal", animal_member.animal)

                # Create a new list of log entries, excluding the one we want to remove.
                new_feeding_log = [
                    log for log in animal_doc.animal_feeding_log
                    if not (log.source_doctype == "Stock Entry" and log.source_document == doc.name)
                ]

                # If the list has changed, update the child table.
                if len(new_feeding_log) < len(animal_doc.animal_feeding_log):
                    animal_doc.animal_feeding_log = new_feeding_log
                    animal_doc.save(ignore_permissions=True)
                    animals_updated += 1

            if animals_updated > 0:
                frappe.msgprint(
                    _("The direct feeding log entry has been removed from {0} animals.")
                    .format(animals_updated)
                )
