// Copyright (c) 2025, aminos and contributors
// For license information, please see license.txt

frappe.ui.form.on('Group Vaccination', {
    onload: function(frm) {
        // Make the table read-only.
        frm.get_field('animals').grid.cannot_add_rows = true;
        frm.get_field('animals').grid.cannot_delete_rows = true;
    },

    refresh: function(frm) {
        // On every refresh, ensure the UI state is correct.
        update_animal_list_visibility(frm);
    },

    livestock_group: function(frm) {
        // If the group changes, we must re-evaluate the animal list.
        update_animal_list_visibility(frm);
    },

    is_flock: function(frm) {
        // If the checkbox changes, this is the primary trigger to show/hide the list.
        update_animal_list_visibility(frm);
    }
});

function update_animal_list_visibility(frm) {
    if (frm.doc.is_flock) {
        // SCENARIO 1: The user has checked "Vaccinate as a Single Flock".
        // HIDE the animal list section.
        frm.toggle_display("animals_vaccinated_section", false);
        frm.clear_table("animals");
        frm.refresh_field("animals");
    } else {
        // SCENARIO 2: The user wants to see individual animals.
        // SHOW the animal list section.
        frm.toggle_display("animals_vaccinated_section", true);

        // Now, check if a group has been selected, and if so, populate the list.
        if (frm.doc.livestock_group) {
            frm.clear_table("animals");
            frm.dashboard.set_headline_alert('Fetching animal list...');

            frappe.call({
                method: 'agriculture_management.livestock.api.get_animals_in_group',
                args: { group_name: frm.doc.livestock_group },
                callback: function(r) {
                    if (r.message && r.message.length > 0) {
                        r.message.forEach(animal => {
                            frm.add_child('animals', { animal: animal.animal });
                        });
                        frm.dashboard.clear_headline(8000);
                    } else {
                        frm.dashboard.set_headline_alert('The selected group has no active animals.');
                    }
                    frm.refresh_field('animals');
                }
            });
        } else {
            // If no group is selected, just ensure the table is empty.
            frm.clear_table("animals");
            frm.refresh_field("animals");
            frm.dashboard.clear_headline();
        }
    }
}