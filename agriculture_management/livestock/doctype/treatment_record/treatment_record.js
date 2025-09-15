// Copyright (c) 2025, aminos and contributors
// For license information, please see license.txt

frappe.ui.form.on('Treatment Record', {
    refresh: function(frm) {
        check_withdrawal_period(frm);
    },
    animal: function(frm) {
        check_withdrawal_period(frm);
    },
    date_of_treatment: function(frm) {
        check_withdrawal_period(frm);
    },
    milk_withdrawal_period: function(frm) {
        check_withdrawal_period(frm);
    },
    meat_withdrawal_period: function(frm) {
        check_withdrawal_period(frm);
    }
});

function check_withdrawal_period(frm) {
    // --- THIS IS THE CRITICAL FIX ---
    // If the document is already submitted (docstatus=1), DO NOT change any values.
    // Just display the alert.
    if (frm.doc.docstatus === 1) {
        // Display logic for submitted docs (e.g., the alert) can go here if needed,
        // but we will NOT call frm.set_value.
        return;
    }
    // --- END OF FIX ---

    if (!frm.doc.animal || !frm.doc.date_of_treatment) {
        frm.dashboard.clear_headline();
        return;
    }

    let milk_days = frm.doc.milk_withdrawal_period || 0;
    let meat_days = frm.doc.meat_withdrawal_period || 0;
    let longest_period = Math.max(milk_days, meat_days);
    
    if (longest_period > 0) {
        let new_end_date_str = frappe.datetime.add_days(frm.doc.date_of_treatment, longest_period);
        // This is safe because we are only in this block if docstatus is 0.
        frm.set_value('withdrawal_end_date', new_end_date_str);
    } else {
        frm.set_value('withdrawal_end_date', null);
        frm.dashboard.clear_headline();
        return;
    }

    frappe.db.get_value("Animal", frm.doc.animal, "in_withdrawal_until")
        .then(r => {
            let existing_end_date_str = r.message.in_withdrawal_until;
            let new_end_date_str = frm.doc.withdrawal_end_date;

            if (existing_end_date_str && frappe.datetime.get_diff(existing_end_date_str, frappe.datetime.now_date()) >= 0) {
                if (frappe.datetime.get_diff(new_end_date_str, existing_end_date_str) > 0) {
                    frm.dashboard.set_headline_alert(
                        `<strong>Warning:</strong> This will <strong>extend</strong> the animal's withdrawal period to <strong>${frappe.datetime.str_to_user(new_end_date_str)}</strong>.`, 'orange'
                    );
                } else {
                    frm.dashboard.set_headline_alert(
                        `<strong>Notice:</strong> This is covered by a longer withdrawal period ending on <strong>${frappe.datetime.str_to_user(existing_end_date_str)}</strong>.`, 'blue'
                    );
                }
            } else {
                frm.dashboard.clear_headline();
            }
        });
}