/*
* This script customizes the List View for the Dosing Log DocType.
*/
/*
* dosing_log_list.js
* This is the final, enhanced version of the List View script for Dosing Log.
* It includes advanced, conditional cascading filters.
*/
frappe.listview_settings['Dosing Log'] = {
    // Add the fields to the filter area so we can control them
    add_fields: ["company", "hydroponic_system", "crop_cycle"],

    onload: function(list_view) {
        
        // --- Filter for Hydroponic System ---
        // This filter now depends on the 'company' filter.
		if (list_view.page.fields_dict.hydroponic_system) {
			list_view.page.fields_dict.hydroponic_system.get_query = function() {
                
                // 1. Start with the base filters that are always active.
                let filters = {
                    "asset_category": ["in", ["Hydroponic Systems", "Hydroponic Equipments"]],
                    "status": ["!=", "Cancelled"]
                };

                // 2. Get the current value of the company filter.
                let company = list_view.page.fields_dict.company.get_value();

                // 3. Conditionally add the company filter ONLY if a company is selected.
                if (company) {
                    filters.company = company;
                }

                // 4. Return the final filter object.
				return { "filters": filters };
			};
		}

        // --- Filter for Crop Cycle ---
        // This filter now depends on both 'company' and 'hydroponic_system'.
        if (list_view.page.fields_dict.crop_cycle) {
			list_view.page.fields_dict.crop_cycle.get_query = function() {
                
                // 1. Start with the base filters.
                let filters = {
                    "growth_method": "Hydroponic",
                    "status": ["!=", "Completed"]
                };

                // 2. Get the current values of the parent filters.
                let company = list_view.page.fields_dict.company.get_value();
                let system = list_view.page.fields_dict.hydroponic_system.get_value();

                // 3. Conditionally add the filters.
                if (company) {
                    filters.company = company;
                }
                if (system) {
                    filters.hydroponic_system = system;
                }

                // 4. Return the final filter object.
				return { "filters": filters };
			};
		}

        // --- Add 'on change' handlers to clear dependent filters ---
        // This provides a better user experience.
        list_view.page.fields_dict.company.on_change = () => {
            list_view.page.fields_dict.hydroponic_system.set_value("");
            list_view.page.fields_dict.crop_cycle.set_value("");
        };

        list_view.page.fields_dict.hydroponic_system.on_change = () => {
            list_view.page.fields_dict.crop_cycle.set_value("");
        };
	}
};