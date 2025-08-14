// This script runs on the Livestock form in the browser
frappe.ui.form.on('Livestock', {
    // The 'setup' event is the best place to define filters.
    // It runs once when the form is being prepared, ensuring the filter is always ready.
    setup: function(frm) {
        // Target the child table field.
        frm.set_query('mate', 'breeding_history', function(doc, cdt, cdn) {
            // doc: The parent document (the main Livestock record)
            // cdt: Child Doctype name ('Breeding History')
            // cdn: Child Doctype row name

            // Start with a base set of filters
            let filters = {
                // Filter 1: Only show animals that are 'Active'
                'status': 'Active',

                // Filter 2: The animal cannot be itself.
                'name': ['!=', doc.name],

                // *** NEW FILTER ADDED HERE ***
                // Filter 3: The species must match the current animal's species.
                'species': doc.species
            };

            // Filter 4: Check the gender of the current animal
            if (doc.gender) {
                // Determine the opposite gender to search for
                let opposite_gender = doc.gender === 'Female' ? 'Male' : 'Female';

                // Add the gender filter to our list
                filters['gender'] = opposite_gender;
            }

            // Return the filters object. This is what the link field will use
            // for its popup query.
            return {
                filters: filters
            };
        });
    },
      refresh: function(frm) {

        // --- Block 1: "Create Serial No" button logic (your existing code) ---
        // This button will only be shown if the conditions are met.
        if (!frm.is_new() && frm.doc.is_serialized_item && !frm.doc.serial_no) {
            frm.add_custom_button(__('Create Serial No'), function() {
                frm.call({
                    method: 'agriculture_management.livestock.api.create_serial_no_for_livestock',
                    args: {
                        doc_name: frm.doc.name
                    },
                    callback: function(r) {
                        if (r.message) {
                            frm.set_value('serial_no', r.message);
                            frm.refresh_field('serial_no');
                            frappe.show_alert({message: `Serial No ${r.message} created.`, indicator: 'green'});
                        }
                    }
                });
            }).addClass('btn-primary');
        }


        // --- Block 2: "Fetch and Populate Offspring" logic (the new code) ---
        // This will run for any saved document that has an 'offspring_list' table.
        if (!frm.is_new() && frm.doc.name && frm.fields_dict.offspring_list) {
            
            // Set the table to read-only and show a loading message
            frm.fields_dict.offspring_list.df.cannot_add_rows = true;
            frm.fields_dict.offspring_list.grid.wrapper.find('.grid-empty-row').html(__('Loading Offspring...'));
            
            frappe.call({
                method: "agriculture_management.livestock.api.get_offspring_and_mates",
                args: {
                    animal_id: frm.doc.name
                },
                callback: function(r) {
                    // Always clear the table before populating
                    frm.clear_table('offspring_list');

                    if (r.message && r.message.length > 0) {
                        // Loop through the data and add rows
                        r.message.forEach(offspring_data => {
                            frm.add_child('offspring_list', {
                                offspring: offspring_data.offspring,
                                mate: offspring_data.mate,
                                date_of_birth: offspring_data.date_of_birth,
                                gender: offspring_data.gender
                            });
                        });
                    } else {
                        // If no data, show an informative message
                        frm.fields_dict.offspring_list.grid.wrapper.find('.grid-empty-row').html(__('No Offspring Found'));
                    }
                    
                    // Refresh the grid to display the new data
                    frm.refresh_field('offspring_list');
                }
            });
        }
        // --- End of Offspring block ---

    }, // End of the 'refresh' function
    dam_mother: function(frm) {
        // Only run if the Acquisition Type is 'Birth' and a Dam is selected
        if (frm.doc.acquisition_type === 'Birth' && frm.doc.dam_mother) {
            
            // --- THIS IS THE CORRECTED CALL ---
            frappe.db.get_list('Breeding History', {
                // The 'parent' condition now goes INSIDE the 'filters' object
                filters: {
                    'parent': frm.doc.dam_mother,
                    'outcome': 'Successful'
                },
                fields: ['mate'],
                order_by: 'breeding_date desc',
                limit: 1
            }).then(result => {
                if (result && result.length > 0 && result[0].mate) {
                    // Set the value in the sire_father field
                    frm.set_value('sire_father', result[0].mate);
                    frappe.show_alert({message: __('Sire (Father) auto-populated from breeding history.'), indicator: 'green'});
                }
            });
            // --- END OF CORRECTION ---
        }
    }


});

// This targets the CHILD TABLE named 'Breeding History'
// The fieldname for the child table in the Livestock doctype is likely 'breeding_history'
frappe.ui.form.on('Breeding History', {
    
    // This event fires whenever the 'breeding_date' field in any row is changed
    breeding_date: function(frm, cdt, cdn) {
        // frm: the main form object (the parent Livestock document)
        // cdt: the child doctype name ('Breeding History')
        // cdn: the child document's unique name (the row ID)
        
        let row = locals[cdt][cdn]; // Get the specific row data that was changed

        // Only proceed if the breeding date is set
        if (row.breeding_date) {
            
            // Call our Python API function from api.py
            frappe.call({
                method: "agriculture_management.livestock.api.get_gestation_period", // The full path to the function
                args: {
                    species: frm.doc.species // Pass the species from the main form
                },
                callback: function(r) {
                    // This function runs when the server sends back a response
                    if (r.message) {
                        let gestation_days = r.message;
                        
                        // Use Frappe's datetime utility to add days to the date
                        let expected_due_date = frappe.datetime.add_days(row.breeding_date, gestation_days);
                        
                        // Set the calculated value back into the 'expected_due_date' field FOR THAT ROW
                        frappe.model.set_value(cdt, cdn, 'expected_due_date', expected_due_date);
                    }
                }
            });
        }
    }
});