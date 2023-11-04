// Copyright (c) 2023, aminos and contributors
// For license information, please see license.txt

frappe.ui.form.on("OWM Setting", {
    refresh(frm) {

    },
    "chk_enable": function (frm) {
        if (frm.doc.chk_enable == false) {
            frm.fields_dict.api_key.toggle(false);
        } else
            frm.fields_dict.api_key.toggle(true);
    },
});