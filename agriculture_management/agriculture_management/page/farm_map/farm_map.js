frappe.pages['farm-map'].on_page_load = function(wrapper) {
    const page = frappe.ui.make_app_page({
        parent: wrapper,
        title: 'Farm Map',
        single_column: true
    });
    // Store a reference to the page object on the wrapper for wider access
    $(wrapper).data('page', page);

    page.add_field({ label: __("Company"), fieldname: "company", fieldtype: "Link", options: "Company", default: frappe.defaults.get_default("company"), change: () => fetchDataAndRender(page) });
    page.add_field({ label: __("Show Active Systems Only"), fieldname: "show_active_only", fieldtype: "Check", default: 1, change: () => renderFarmSystems(page) });

    const page_content = $(`<div class="farm-map-container"><div id="farm-layout-grid"></div></div>`).appendTo(page.body);
    page.set_primary_action("Refresh", () => fetchDataAndRender(page));

    fetchDataAndRender(page);
}

// Fetches data from the server and then calls the render function
function fetchDataAndRender(page) {
    const grid = $(page.body).find('#farm-layout-grid');
    const company = page.fields_dict.company.get_value();
    if (!company) {
        grid.html('<div class="text-center text-muted p-4"><h3>Please select a Company.</h3></div>');
        return;
    }
    grid.html(`<p class="text-muted">Loading layout for ${company}...</p>`);

    frappe.call({
        method: "agriculture_management.agriculture_management.api.get_farm_map_data", // Using the path you confirmed is correct
        args: { company: company }
    }).then(r => {
        let farm_data = r.message;
        if (!farm_data || (!farm_data.hydroponics && !farm_data.livestock)) {
            grid.html('<div class="text-center text-muted p-4"><h3>No Farm Areas Found.</h3></div>');
            page.farm_data = []; // Ensure data is cleared
            return;
        }
        // Store the master data on the page object
        page.farm_data = [...(farm_data.hydroponics || []), ...(farm_data.livestock || [])];

        // Perform the initial render
        renderFarmSystems(page);
    }).fail(() => {
        // Handle API call failure gracefully
        const grid = $(page.body).find('#farm-layout-grid');
        grid.html('<div class="text-center text-danger p-4"><h3>Could not load Farm Map data.</h3><p>Please check the server logs for more information.</p></div>');
    });
}

// Renders the farm systems using the data stored in page.farm_data
function renderFarmSystems(page) {
    const grid = $(page.body).find('#farm-layout-grid');
    const show_active_only = page.fields_dict.show_active_only.get_value();

    const all_systems = page.farm_data || [];
    const systems_to_display = show_active_only
        ? all_systems.filter(area => area.active_content > 0)
        : all_systems;

    grid.empty();

    if (systems_to_display.length === 0) {
        grid.html('<div class="text-center text-muted p-4"><h3>No matching Farm Areas to display.</h3></div>');
        return;
    }

    const render_area_card = (area) => {
        let icon = area.type === 'Hydroponic System' ? 'fa fa-leaf' : 'fa fa-paw';
        let inactive_count = area.type === 'Hydroponic System' && area.contents ? area.contents.filter(z => z.status === 'Inactive' || z.status === 'Out of Order').length : 0;
        let occupancy_html = area.occupancy_rate != null ? `<div class="progress" style="height: 8px;"><div class="progress-bar bg-success" role="progressbar" style="width: ${area.occupancy_rate}%"></div></div>` : '';

        let area_meta;
        if (area.active_content > 0) {
            area_meta = `${area.type} | ${area.active_content} / ${area.total_content} Active`;
        } else {
            area_meta = `${area.type} | <span class="text-muted">Empty</span>`;
        }
        if (inactive_count > 0) {
            area_meta += ` | <span class="text-danger">${inactive_count} Inactive</span>`;
        }

        let card = $(`<div class="farm-area" data-area-name="${area.name}"><div class="farm-area-header"><i class="${icon} area-icon"></i><h5>${area.display_name}</h5></div><p class="area-meta">${area_meta}</p>${occupancy_html}</div>`);

        // ### FIX: Changed from using 'wrapper' to the 'page' object which is in scope ###
        card.on('click', () => {
            const master_list = page.farm_data; // This is the corrected line
            const area_details = master_list.find(a => a.name === area.name);
            if (area_details) {
                showAreaDetailsDialog(area_details);
            }
        });
        return card;
    };

    const hydroponics_systems = systems_to_display.filter(s => s.type === 'Hydroponic System');
    const livestock_systems = systems_to_display.filter(s => s.type === 'Livestock Area');

    if (hydroponics_systems.length > 0) {
        grid.append('<h3 class="section-title">Hydroponics</h3>');
        const section_grid = $('<div class="section-grid"></div>').appendTo(grid);
        hydroponics_systems.forEach(area => section_grid.append(render_area_card(area)));
    }

    if (livestock_systems.length > 0) {
        grid.append('<h3 class="section-title">Livestock</h3>');
        const section_grid = $('<div class="section-grid"></div>').appendTo(grid);
        livestock_systems.forEach(area => section_grid.append(render_area_card(area)));
    }
}


function naturalSort(a, b) {
    const nameA = a.zone_name || a.name;
    const nameB = b.zone_name || b.name;
    const re = /(\d+)/g;
    const partsA = nameA.split(re);
    const partsB = nameB.split(re);

    for (let i = 0; i < Math.min(partsA.length, partsB.length); i++) {
        const partA = partsA[i];
        const partB = partsB[i];
        if (i % 2 === 1) {
            const numA = parseInt(partA, 10);
            const numB = parseInt(partB, 10);
            if (numA !== numB) return numA - numB;
        } else {
            if (partA !== partB) return partA.localeCompare(partB);
        }
    }
    return partsA.length - partsB.length;
}
function showAreaDetailsDialog(area_data) {
    let dialog = new frappe.ui.Dialog({ title: `Layout for ${area_data.display_name}`, size: 'extra-large' });
    const wrapper = $(dialog.body).addClass("visual-layout-dialog");
    const details_container = $('<div class="visual-layout-wrapper"></div>').appendTo(wrapper);

    if (area_data.type === 'Hydroponic System') {
        const zones = area_data.contents;
        const { racks = 1, tiers = 1, gullies = 1, prefix = 'Rack' } = area_data.layout;
        if (!zones || zones.length === 0) {
            details_container.html('<p class="text-muted">This system has no growing zones defined.</p>');
            dialog.show();
            return;
        }

        const master_detail_container = $('<div class="master-detail-container"></div>').appendTo(details_container);
        const rack_navigator = $('<div class="rack-navigator"></div>').appendTo(master_detail_container);
        const detail_pane_wrapper = $('<div class="detail-pane-wrapper"></div>').appendTo(master_detail_container);

        zones.sort(naturalSort);

        // First, process all zones and group them by rack with calculated summaries.
        const zones_per_rack = tiers * gullies;
        const rack_data = [];

        for (let r = 1; r <= racks; r++) {
            const rack_index = r - 1;
            const start_index = rack_index * zones_per_rack;
            const end_index = start_index + zones_per_rack;
            const zones_in_this_rack = zones.slice(start_index, end_index);
            
            // NEW: Added harvest_ready to the counts
            const counts = { optimal: 0, maintenance: 0, inactive: 0, harvest_ready: 0 };
            zones_in_this_rack.forEach(zone => {
                if (!zone) return;
                
                if (zone.status === 'Harvest Ready') { // NEW: Count for Harvest Ready status
                    counts.harvest_ready++;
                } else if (zone.current_crop && zone.status === 'Active') {
                    counts.optimal++;
                } else if (zone.status === 'Under Maintenance') {
                    counts.maintenance++;
                } else if (zone.status === 'Inactive' || zone.status === 'Out of Order') {
                    counts.inactive++;
                }
            });

            rack_data.push({
                id: r,
                prefix: prefix,
                zones: zones_in_this_rack,
                summary_counts: counts
            });
        }

        // Now, build the UI using the pre-processed rack_data.
        rack_data.forEach((data, index) => {
            const is_active = index === 0;

            // NEW: Added the harvest_ready span to the summary
            const summary_html = `<div class="rack-summary">
                <span class="status-optimal" title="Optimal"><i class="fa fa-check-circle"></i> ${data.summary_counts.optimal}</span>
                <span class="status-harvest-ready" title="Harvest Ready"><i class="fa fa-inbox"></i> ${data.summary_counts.harvest_ready}</span>
                <span class="status-maintenance" title="Needs Attention"><i class="fa fa-exclamation-circle"></i> ${data.summary_counts.maintenance}</span>
                <span class="status-inactive" title="Inactive"><i class="fa fa-times-circle"></i> ${data.summary_counts.inactive}</span>
            </div>`;
            rack_navigator.append(`<div class="rack-nav-item ${is_active ? 'active' : ''}" data-rack-id="${data.id}">
                <div class="rack-nav-name">${data.prefix} ${data.id}</div>${summary_html}</div>`);

            const detail_pane = $(`<div class="detail-pane ${is_active ? 'active' : ''}" data-rack-id="${data.id}"></div>`).appendTo(detail_pane_wrapper);
            
            // NEW: Added the "Harvest Ready" filter button
            const gully_search_bar = $(`<div class="gully-search-bar"><i class="fa fa-search"></i><input type="text" class="gully-search-input" placeholder="Search gullies in this rack..."></div>
                            <div class="gully-filter-bar">
                                <button class="filter-tag harvest-ready" data-filter="harvest-ready">Harvest Ready</button>
                                <button class="filter-tag maintenance" data-filter="maintenance">Under Maintenance</button>
                                <button class="filter-tag inactive" data-filter="inactive">Inactive</button>
                            </div>`);
            detail_pane.append(gully_search_bar);
            const content_container = $('<div class="detail-pane-content"></div>').appendTo(detail_pane);

            let zone_idx_in_rack = 0;
            for (let t = 1; t <= tiers; t++) {
                content_container.append(`<h4 class="tier-header-alt">Tier ${t}</h4>`);
                const gully_grid = $('<div class="gully-grid"></div>').appendTo(content_container);
                for (let g = 1; g <= gullies; g++) {
                    const zone = data.zones[zone_idx_in_rack];
                    let status_key = 'empty', status_text = 'Empty';
                    
                    if (zone) {
                        // NEW: Added logic for Harvest Ready status on the gully card
                        if (zone.status === 'Harvest Ready') {
                            status_key = 'harvest-ready';
                            status_text = 'Harvest Ready';
                        } else if (zone.current_crop && zone.status === 'Active') {
                            status_key = 'optimal';
                            status_text = 'Optimal';
                        } else if (zone.status === 'Under Maintenance') {
                            status_key = 'maintenance';
                            status_text = 'Under Maintenance';
                        } else if (zone.status === 'Inactive' || zone.status === 'Out of Order') {
                            status_key = 'inactive';
                            status_text = 'Inactive';
                        }
                    }

                    const zone_display_name = zone ? (zone.zone_name || zone.name) : "Empty Slot";
                    const href = zone ? `/app/growing-zone/${zone.name}` : '#';
                    gully_grid.append(`<a href="${href}" class="gully-card status-${status_key}" data-status="${status_key}">
                        <div class="gully-card-name">${zone_display_name}</div>
                        <div class="gully-card-status">${status_text}</div>
                    </a>`);
                    zone_idx_in_rack++;
                }
            }
            content_container.append('<div class="no-results-message" style="display: none;">No gullies found matching your search.</div>');
        });
        
        // This entire block of event handlers remains the same, but must be inside the function scope.
        function updateGullyVisibility(pane) {
            const searchTerm = pane.find('.gully-search-input').val().toLowerCase();
            const activeFilter = pane.find('.filter-tag.active').data('filter');
            const gullyCards = pane.find('.gully-card');
            let visibleCards = 0;

            gullyCards.each(function() {
                const card = $(this);
                const cardName = card.find('.gully-card-name').text().toLowerCase();
                const cardStatus = card.data('status');
                const filterMatch = !activeFilter || cardStatus === activeFilter;
                const searchMatch = cardName.includes(searchTerm);

                if (filterMatch && searchMatch) {
                    card.show();
                    visibleCards++;
                } else {
                    card.hide();
                }
            });
            pane.find('.no-results-message').toggle(visibleCards === 0);
        }

        wrapper.on('click', '.filter-tag', function() {
            const button = $(this);
            const pane = button.closest('.detail-pane');
            if (button.hasClass('active')) {
                button.removeClass('active');
            } else {
                button.siblings('.filter-tag').removeClass('active');
                button.addClass('active');
            }
            updateGullyVisibility(pane);
        });

        wrapper.on('keyup', '.gully-search-input', function() {
            const pane = $(this).closest('.detail-pane');
            updateGullyVisibility(pane);
        });

        rack_navigator.on('click', '.rack-nav-item', function() {
            if ($(this).hasClass('active')) return;
            const rack_id = $(this).data('rack-id');
            rack_navigator.find('.rack-nav-item').removeClass('active');
            $(this).addClass('active');
            detail_pane_wrapper.find('.detail-pane').removeClass('active');
            detail_pane_wrapper.find(`.detail-pane[data-rack-id="${rack_id}"]`).addClass('active');
        });

    } else if (area_data.type === 'Livestock Area') {
        const groups = area_data.contents;
        if (groups?.length) {
            const grid = $('<div class="livestock-grid-alt"></div>');
            groups.forEach(group => {
                grid.append($(`<a href="/app/livestock-group/${group.name}" class="livestock-card-alt">
                        <div class="livestock-card-header"><i class="fa fa-paw livestock-icon-alt"></i><div class="livestock-card-name">${group.group_name}</div></div>
                        <div class="livestock-card-details"><span><i class="fa fa-tag fa-fw"></i> ${group.species || 'N/A'}</span><span><i class="fa fa-calculator fa-fw"></i> ${group.total_animals || 0}</span></div>
                        <div class="livestock-card-location"><i class="fa fa-map-marker fa-fw"></i> ${group.group_location || 'No Location'}</div>
                    </a>`));
            });
            details_container.append(grid);
        } else {
            details_container.html(`<div class="text-center text-muted p-4"><h3>This area has no active groups.</h3></div>`);
        }
    }

    dialog.show();
}
frappe.ui.theme.on_change(() => {
    document.body.classList.toggle("theme-dark", frappe.boot.user.theme === "Dark");
});
