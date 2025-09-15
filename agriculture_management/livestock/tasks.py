import frappe
from frappe.utils import nowdate, getdate, date_diff, add_days, getdate
from frappe.desk.doctype.notification_log.notification_log import enqueue_create_notification


def check_for_due_health_events():
    """
    Scheduled daily task to check for due vaccinations and create ToDos.
    """
    settings = frappe.get_doc("Livestock Settings")
    if not settings.alert_recipient:
        return  # Exit if no recipient is set

    # Get all vaccination schedule templates
    schedules = frappe.get_all(
        "Vaccination Schedule", fields=["name", "species"])

    for schedule_details in schedules:
        schedule = frappe.get_doc(
            "Vaccination Schedule", schedule_details.name)

        # Find all active animals of the matching species
        active_animals = frappe.get_all("Animal",
                                        filters={"status": "Active",
                                                 "species": schedule.species},
                                        fields=["name", "date_of_birth"]
                                        )

        for animal in active_animals:
            age_in_days = date_diff(nowdate(), animal.date_of_birth)

            for event in schedule.events:
                if age_in_days == event.age_to_administer_days:
                    # Create a unique description to prevent duplicates
                    description = f"Health Alert for {animal.name}: Due for '{event.health_event}' ({event.item})."

                    # IDEMPOTENCY CHECK: Prevent creating duplicate ToDos
                    if not frappe.db.exists("ToDo", {
                        "reference_type": "Animal",
                        "reference_name": animal.name,
                        "description": description,
                        "status": "Open"
                    }):
                        frappe.new_doc("ToDo", {
                            "owner": settings.alert_recipient,
                            "reference_type": "Animal",
                            "reference_name": animal.name,
                            "description": description
                        }).insert(ignore_permissions=True)


def check_for_pasture_moves():
    """
    Scheduled daily task that checks all active Grazing Plans and creates
    a ToDo reminder and a real-time Notification if a pasture move is
    scheduled for the next day.
    """
    frappe.logger().info("--- Running scheduled job: check_for_pasture_moves ---")

    try:
        settings = frappe.get_doc("Livestock Settings")
        if not settings.alert_recipient:
            frappe.logger().warning(
                "Livestock pasture move check skipped: 'Alert Recipient' not set in Livestock Settings.")
            return

        frappe.logger().info(
            f"Alert Recipient found: {settings.alert_recipient}")

        tomorrow = add_days(nowdate(), 1)
        active_plans = frappe.get_all("Grazing Plan", filters={
                                      "status": "Active"}, fields=["name", "livestock_group"])

        for plan_header in active_plans:
            plan_doc = frappe.get_doc("Grazing Plan", plan_header.name)

            for rotation in plan_doc.pasture_rotation:
                if rotation.planned_move_in_date and getdate(rotation.planned_move_in_date) == getdate(tomorrow):
                    subject = f"Pasture Move: Herd '{plan_header.livestock_group}' to '{rotation.pasture}'"

                    if not frappe.db.exists("ToDo", {"reference_type": "Grazing Plan", "reference_name": plan_doc.name, "description": subject, "status": "Open"}):

                        todo = frappe.new_doc("ToDo")
                        # You mentioned 'allocated_to' works, so we will use that.
                        todo.update({
                            "allocated_to": settings.alert_recipient,
                            "reference_type": "Grazing Plan",
                            "reference_name": plan_doc.name,
                            "description": subject
                        })
                        todo.insert(ignore_permissions=True)
                        frappe.logger().info(
                            f"Successfully created ToDo for: {subject}")

                        # --- BULLETPROOF NOTIFICATION BLOCK ---
                        try:
                            notification_doc = {
                                "type": "Alert",
                                "document_type": "Grazing Plan",
                                "document_name": plan_doc.name,
                                "subject": subject,
                                "from_user": "Administrator",
                                "for_user": settings.alert_recipient
                            }

                            frappe.logger().info(
                                f"Attempting to enqueue notification: {notification_doc}")
                            enqueue_create_notification(
                                [settings.alert_recipient], notification_doc)
                            frappe.logger().info(
                                f"Successfully enqueued notification for user {settings.alert_recipient}")

                        except Exception as e:
                            # If anything goes wrong inside this block, log it with a full traceback
                            frappe.log_error(
                                title="Failed to Enqueue Notification", message=frappe.get_traceback())
                        # --- END OF BLOCK ---

    except Exception as e:
        frappe.log_error(
            title="Critical Error in check_for_pasture_moves", message=frappe.get_traceback())


def check_withdrawal_periods():
    """
    Scheduled daily task to check for treatment records where the withdrawal
    period has ended and updates their status to 'Completed'.
    """
    frappe.logger().info("Running scheduled job: check_withdrawal_periods")

    records_to_update = frappe.get_all("Treatment Record",
                                       filters={
                                           "status": "Withdrawal Period Active",
                                           "withdrawal_end_date": ("<=", nowdate())
                                       }
                                       )

    for record_data in records_to_update:
        try:
            doc = frappe.get_doc("Treatment Record", record_data.name)
            doc.status = "Completed"
            doc.save(ignore_permissions=True)
            frappe.logger().info(
                f"Updated Treatment Record {doc.name} to Completed.")
        except Exception as e:
            frappe.log_error(
                title=f"Failed to update Treatment Record {record_data.name}", message=frappe.get_traceback())

    # Commit changes made in the loop
    frappe.db.commit()


def process_device_logs():
    """
    Scheduled job that processes raw data from the device integration log.
    Example: Processes weight data from a smart scale.
    """
    unprocessed_logs = frappe.get_all(
        "Device Integration Log", filters={"status": "Unprocessed"})

    for log_info in unprocessed_logs:
        log_doc = frappe.get_doc("Device Integration Log", log_info.name)
        try:
            payload = frappe.parse_json(log_doc.payload)
            tag_id = payload.get("tag_id")
            weight = payload.get("weight")

            if not (tag_id and weight):
                raise ValueError("Payload missing 'tag_id' or 'weight'")

            # Find the livestock animal by its tag ID
            livestock_name = frappe.db.get_value(
                "Animal", {"animal_id_tag_id": tag_id})
            if not livestock_name:
                raise ValueError(f"No livestock found with Tag ID {tag_id}")

            # Update the animal's weight history
            animal = frappe.get_doc("Animal", livestock_name)
            animal.append("weight_history", {
                "date": nowdate(),
                "weight": weight
            })
            animal.save(ignore_permissions=True)

            # Update the log status
            log_doc.status = "Processed"
            log_doc.save(ignore_permissions=True)

        except Exception as e:
            log_doc.status = "Error"
            log_doc.error_message = str(e)
            log_doc.save(ignore_permissions=True)
            frappe.log_error(
                title=f"Error processing Device Log {log_doc.name}")

    frappe.db.commit()
