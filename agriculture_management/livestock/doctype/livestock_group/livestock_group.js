frappe.ui.form.on('Livestock Group', {
    refresh: function(frm) {

        // The main condition: only add the 'Actions' menu for saved documents.
        if (!frm.is_new()) {
            
            // Sub-condition for the "Move Group" button.
            // This button will only be added to the menu if a location is set.
            if (frm.doc.group_location) {
                frm.add_custom_button(__('Move Group'), function() {
                    frappe.prompt({
                        fieldname: 'new_location',
                        label: 'New Location (Warehouse)',
                        fieldtype: 'Link',
                        options: 'Warehouse',
                        reqd: 1
                    }, (values) => {
                        frappe.call({
                            method: 'agriculture_management.livestock.api.move_livestock_group',
                            args: {
                                group_name: frm.doc.name,
                                new_location: values.new_location
                            },
                            callback: function(r) {
                                if(r.message) {
                                    frappe.show_alert({
                                        message: __(`Group moved via Stock Entry: {0}`, [r.message]),
                                        indicator: 'green'
                                    });
                                    frm.reload_doc();
                                }
                            }
                        });
                    });
                }, __('Actions'));
            }

            // The "Create Snapshot" button has no extra conditions, so it will always be added.
            frm.add_custom_button(__('Create Snapshot'), function() {
                frappe.confirm('Are you sure you want to create a new herd snapshot?', () => {
                    frappe.call({
                        method: 'agriculture_management.livestock.api.create_herd_snapshot',
                        args: {
                            livestock_group_name: frm.doc.name
                        },
                        callback: function(r) {
                            if(r.message) {
                                let snapshot_name = r.message;
                                let route = `/app/herd-snapshot/${snapshot_name}`;
                                frappe.show_alert({
                                    message: __("Herd Snapshot created successfully.") +
                                        `<br><a href="${route}"><b>${__('Click here to view Snapshot {0}', [snapshot_name])}</b></a>`,
                                    indicator: 'green'
                                });
                            }
                        }
                    });
                });
            }, __('Actions'));

        } // End of the main 'if (!frm.is_new())' block

    } // End of the 'refresh' function
});