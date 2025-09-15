// Copyright (c) 2025, aminos and contributors
// For license information, please see license.txt

// --- Events for the PARENT 'Feed Formulation' form ---
frappe.ui.form.on("Feed Formulation", {
    // When a row is removed from the table, or when the main date/price list changes,
    // we need to recalculate everything.
    ingredients_remove: function(frm) {
        update_totals(frm);
    },
    buying_price_list: function(frm) {
        // When the price list changes, we must recalculate all rows.
        (frm.doc.ingredients || []).forEach(row => {
            calculate_cost_for_row(frm, row.doctype, row.name);
        });
    },
    date: function(frm) {
        // When the date changes, all prices might be different, so recalculate all rows.
        (frm.doc.ingredients || []).forEach(row => {
            calculate_cost_for_row(frm, row.doctype, row.name);
        });
    },
    validate: function(frm) {
        // Final check before saving.
        update_totals(frm);
        if (Math.abs(frm.doc.total_percentage - 100.0) > 0.001) {
            frappe.throw(__("Total Percentage must be 100%."));
        }
    }
});

// --- Events for each ROW in the 'ingredients' child table ---
frappe.ui.form.on("Feed Formulation Item", {
    // When the user changes the percentage or the item in any row,
    // just recalculate the cost for THAT specific row.
    percentage: function(frm, cdt, cdn) {
        calculate_cost_for_row(frm, cdt, cdn);
    },
    item: function(frm, cdt, cdn) {
        calculate_cost_for_row(frm, cdt, cdn);
    }
});


/**
 * Calculates the cost for a SINGLE ROW in the child table.
 * This is more efficient than recalculating the whole table every time.
 * @param {object} frm - The form object.
 * @param {string} cdt - Child DocType name.
 * @param {string} cdn - Child DocName (row name).
 */
function calculate_cost_for_row(frm, cdt, cdn) {
    let row = locals[cdt][cdn];
    let transaction_date = frm.doc.date || frappe.datetime.now_date();

    if (!row.item || !frm.doc.buying_price_list) {
        frappe.model.set_value(cdt, cdn, 'cost', 0).then(() => update_totals(frm));
        return;
    }

    // --- THIS IS THE DEFINITIVE, COMPATIBLE FIX ---
    // Use frappe.client.get_list with a simple filter, then process the date in the callback.
    frappe.call({
        method: "frappe.client.get_list",
        args: {
            doctype: "Item Price",
            filters: {
                item_code: row.item,
                price_list: frm.doc.buying_price_list
            },
            fields: ["price_list_rate", "valid_from", "valid_upto"]
        },
        callback: function(r) {
            let rate = 0;
            if (r.message) {
                // Filter by date on the client-side.
                for (let price_record of r.message) {
                    let is_valid_from = frappe.datetime.get_diff(transaction_date, price_record.valid_from) >= 0;
                    let is_valid_upto = true;
                    if (price_record.valid_upto) {
                        if (frappe.datetime.get_diff(price_record.valid_upto, transaction_date) < 0) {
                            is_valid_upto = false;
                        }
                    }
                    if (is_valid_from && is_valid_upto) {
                        rate = price_record.price_list_rate;
                        break;
                    }
                }
            }
            
            let cost = (flt(rate) * (flt(row.percentage) / 100.0));
            frappe.model.set_value(cdt, cdn, 'cost', cost).then(() => {
                update_totals(frm);
            });
        }
    });
    // --- END OF FIX ---
}



/**
 * A simple helper function to update the total fields at the bottom of the form.
 * It reads the values that are already in the child table grid.
 * @param {object} frm - The form object.
 */
function update_totals(frm) {
    let total_percentage = 0;
    let total_cost = 0;
    (frm.doc.ingredients || []).forEach(row => {
        total_percentage += flt(row.percentage);
        total_cost += flt(row.cost);
    });
    frm.set_value("total_percentage", total_percentage);
    frm.set_value("total_formulation_cost", total_cost);
    frm.get_field('total_percentage').$wrapper.find('div').css('color',
        Math.abs(total_percentage - 100.0) > 0.001 ? 'red' : 'green');
}