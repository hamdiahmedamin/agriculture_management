// frappe.pages['genealogy-tree'].on_page_load = function(wrapper) {
//     let page = frappe.ui.make_app_page({
//         parent: wrapper,
//         title: 'Livestock Genealogy Tree',
//         single_column: true
//     });

//     // Load the FamilyTree.js library from our app's public assets
//     frappe.require("/assets/agriculture_management/js/familytree.js", () => {
        
//         let $container = $(page.body);
//         $container.html(`
//             <div class="frappe-control" data-fieldname="livestock_filter" style="max-width: 400px; margin-bottom: 20px;"></div>
//             <div id="tree" style="width:100%; height:700px;"></div>
//         `);
        
//         const chart_div = $container.find('#tree').get(0);
//         let family_tree = null; // This will hold our single chart instance

 


//         // Create the filter field to select a single Livestock
//         let livestock_filter = frappe.ui.form.make_control({
//             parent: $container.find('[data-fieldname="livestock_filter"]'),
//             df: {
//                 label: __('Select Livestock'),
//                 fieldname: 'livestock',
//                 fieldtype: 'Link',
//                 options: 'Livestock',
//                 change: () => {
//                     let animal_id = livestock_filter.get_value();
//                     if (animal_id) {
//                         load_full_family_tree(animal_id);
//                     } else {
//                         if (family_tree) {
//                             // The library doesn't have a destroy method, so we just clear the div
//                             $(chart_div).empty(); 
//                             family_tree = null;
//                         }
//                     }
//                 }
//             },
//             render_input: true
//         });

//         function load_full_family_tree(animal_id) {
//             frappe.dom.freeze(__("Loading Full Family Tree..."));

//             frappe.call({
//                 method: "agriculture_management.livestock.page.genealogy_tree.genealogy_tree.get_family_tree_data",
//                 args: { root_animal_id: animal_id },
//                 always: () => {
//                     frappe.dom.unfreeze();
//                 },
//                 callback: function(r) {
//                     if (r.message && r.message.length > 0) {
                        
//                         // Initialize the FamilyTree component
//                         family_tree = new FamilyTree(chart_div, {
//                             nodes: r.message, // Load the full dataset
//                             mouseScrool: FamilyTree.action.zoom,
//                             nodeBinding: {
//                                 field_0: "name", // Binds the 'name' from our data
//                                 img_0: "img"     // Binds the 'img' from our data
//                             },
//                             // Set the starting node for the tree view
//                             nodeId: animal_id
//                         });

//                         // Add a custom event listener for clicks
//                         family_tree.on('click', function (sender, args) {
//                             frappe.set_route("Form", "Livestock", args.node.id);
//                         });

//                     } else {
//                         $(chart_div).html('<p class="text-muted" style="text-align:center;">No genealogy data found.</p>');
//                     }
//                 }
//             });
//         }
//     });
// };

frappe.pages['genealogy-tree'].on_page_load = function(wrapper) {
    let page = frappe.ui.make_app_page({
        parent: wrapper,
        title: 'Livestock Genealogy Tree',
        single_column: true
    });

    // Load the Vis.js library and its required CSS from your app's public assets
    frappe.require([
        "/assets/agriculture_management/js/vis-network.js",
        "/assets/agriculture_management/css/vis-network.css"
    ], () => {
        
        let $container = $(page.body);

        // Create the Frappe-style card layout
        $container.html(`
            <div class="frappe-card genealogy-page-card" style="display: flex; flex-direction: column;">
                <div class="card-body" style="padding-bottom: 0;">
                    <div class="row">
                        <div class="col-md-4" data-fieldname="species_filter_wrapper"></div>
                        <div class="col-md-4" data-fieldname="livestock_filter_wrapper" style="display: none;"></div>
                    </div>
                </div>
                <div class="network-container card-body" style="flex: 1 1 auto; margin-top: 15px; padding: 0;">
                    <div id="tree" style="width:100%; height:100%;"></div>
                </div>
            </div>
        `);
        
        const container = $container.find('#tree').get(0);
        const livestock_filter_wrapper = $container.find('[data-fieldname="livestock_filter_wrapper"]');
        let network = null;
        let livestock_filter = null;
        let current_nodes_data = null;

        // Function to dynamically set the card's height for a responsive layout
        function set_card_height() {
            let page_head_height = $(".page-head").height() + 30; // 30 for padding
            let page_content = $container.find(".genealogy-page-card");
            page_content.css("height", `calc(100vh - ${page_head_height}px)`);
        }

        set_card_height();
        $(window).on("resize", set_card_height);

       
       // --- THE FINAL, VERIFIED BUTTON LOGIC ---

        // 1. Create the standalone buttons. These are correct.
        let reset_button = page.add_inner_button(__("Reset"), () => {
            species_filter.set_value('');
        });
        
        let center_button = page.add_inner_button(__("Center Chart"), () => {
            if (network) network.fit({ animation: { duration: 800 } });
        });

      // 2. Create the Export dropdown menu correctly.
        // This will create a button labeled "Export" with a dropdown.
        let export_button = page.add_inner_button(__("Export"), () => {
            // This primary action can be empty or do something like export PNG by default
        });
        // Now, we modify this button to be a dropdown.
        let $export_btn_group = $(export_button).parent();
        $export_btn_group.addClass("dropdown");
        $(export_button).addClass("dropdown-toggle").attr("data-toggle", "dropdown");
        // Add the dropdown menu items
        let export_menu = $(`<ul class="dropdown-menu">
            <li><a class="dropdown-item" data-export-type="png">${__("Export as PNG")}</a></li>
            <li><a class="dropdown-item" data-export-type="jpg">${__("Export as JPG")}</a></li>
            <li><a class="dropdown-item" data-export-type="csv">${__("Export as CSV")}</a></li>
        </ul>`).appendTo($export_btn_group);

        export_menu.on("click", "[data-export-type]", function() {
            let export_type = $(this).data("export-type");
            if (!network || !current_nodes_data) {
                frappe.msgprint(__("Please generate a tree first."));
                return;
            }
            if (export_type === "png") export_network_as_png();
            else if (export_type === "csv") export_network_as_csv();
            else if (export_type === "jpg") export_network_as_jpg();
        });
        
        function show_action_buttons() {
            reset_button.parent().show();
            center_button.parent().show();
            $export_btn_group.show();
        }
        function hide_action_buttons() {
            reset_button.parent().hide();
            center_button.parent().hide();
            $export_btn_group.hide();
        }
        hide_action_buttons();

        // --- END OF FINAL BUTTON LOGIC ---

        // --- Two-Step Filter Logic ---
        let species_filter = frappe.ui.form.make_control({
            parent: $container.find('[data-fieldname="species_filter_wrapper"]'),
            df: {
                label: __('Species'),
                fieldname: 'species',
                fieldtype: 'Link',
                options: 'Livestock Species',
                change: () => {
                    let species = species_filter.get_value();
                    create_livestock_filter(species);
                    if (species) {
                        livestock_filter_wrapper.show();
                    } else {
                        livestock_filter_wrapper.hide();
                        if (network) network.destroy();
                        $(container).empty();
                        hide_action_buttons();
                    }
                }
            },
            render_input: true
        });

        function create_livestock_filter(species) {
            livestock_filter_wrapper.empty();
            livestock_filter = frappe.ui.form.make_control({
                parent: livestock_filter_wrapper,
                df: {
                    label: __('Select Livestock'),
                    fieldname: 'livestock',
                    fieldtype: 'Link',
                    options: 'Livestock',
                    get_query: () => { return { filters: { 'species': species || '' } }; },
                    change: () => {
                        let animal_id = livestock_filter.get_value();
                        if (animal_id) {
                            load_and_render_network(animal_id);
                        } else {
                            if (network) network.destroy();
                            $(container).empty();
                            hide_action_buttons();
                        }
                    }
                },
                render_input: true
            });
        }
        create_livestock_filter(null);
        
        // --- Main Data and Rendering Functions ---
        function load_and_render_network(animal_id) {
            frappe.dom.freeze(__("Loading Family Tree..."));
            frappe.call({
                method: "agriculture_management.livestock.page.genealogy_tree.genealogy_tree.get_full_family_tree",
                args: { root_animal_id: animal_id },
                always: () => { frappe.dom.unfreeze(); },
                callback: function(r) {
                    if (r.message && r.message.nodes) {
                        current_nodes_data = r.message.nodes;
                        const fallback_image = "/assets/agriculture_management/images/livestock.png";
                        
                        r.message.nodes.forEach(node => {
                                // --- Step 1: Handle images as before ---
                            node.brokenImage = fallback_image;
                            if (!node.image) node.image = fallback_image;

                            // --- Step 2: Create a real HTML element for the title ---
                            const titleElement = document.createElement('div');
                            titleElement.style.padding = '5px';
                            titleElement.style.textAlign = 'left';
                            titleElement.innerHTML = `
                                <b>ID:</b> ${node.animal_id_tag_id || node.id}<br>
                                <b>Name:</b> ${node.label || 'N/A'}<br>
                                <b>Breed:</b> ${node.breed || 'N/A'}<br>
                                <b>Date of Birth:</b> ${node.date_of_birth || 'N/A'}<br>
                                <b>Health Status:</b> ${node.health_status || 'N/A'}<br>
                                <b>Pen:</b> ${node.location_pen || 'N/A'}<br>
                                <b>Weight:</b> ${node.current_weight || 'N/A'}
                            `;
                            // Assign the ELEMENT, not the string, to the title property
                            node.title = titleElement;
                            // --- END OF FIX ---
                            
                            // If this node is the one the user selected, make it stand out
                            if (node.id === animal_id) {
                                node.borderWidth = 5; // Make the border thicker
                                node.color = {
                                    border: '#ffd700', // A gold color for highlight
                                    highlight: { border: '#ffd700' }
                                };
                                node.font = {
                                    size: 16, // Make the font slightly larger
                                    face: 'Inter, sans-serif',
                                    bold: {
                                        color: '#333'
                                    }
                                };
                            }
                        });

                        const nodes = new vis.DataSet(r.message.nodes);
                        const edges = new vis.DataSet(r.message.edges);

                        const options = {
                            layout: { hierarchical: { direction: "UD", sortMethod: "directed", levelSeparation: 80, nodeSpacing: 120 } },
                            edges: { color: { color: '#adb5bd', highlight: '#495057' }, smooth: { type: 'cubicBezier', forceDirection: 'vertical', roundness: 0.4 } },
                            nodes: { borderWidth: 3, size: 35, font: { size: 14, face: 'Inter, sans-serif' } },
                            groups: { Male: { color: { background: '#eaf4ff', border: '#4a90e2' } }, Female: { color: { background: '#fdeff2', border: '#e6557c' } } },
                            physics: { enabled: false },
                            interaction: { zoomView: true, dragView: true, tooltipDelay: 800 }
                        };

                        if (network) network.destroy();
                        network = new vis.Network(container, { nodes: nodes, edges: edges }, options);

                        network.on("doubleClick", function (params) {
                            if (params.nodes.length > 0) 
                                frappe.set_route("Form", "Livestock", params.nodes[0]);
                        });
                        network.fit({ animation: { duration: 800 } });
                        show_action_buttons();
                    } else {
                        if (network) network.destroy();
                        $(container).empty();
                        current_nodes_data = null;
                        hide_action_buttons();
                    }
                }
            });
        }
        
        function export_network_as_png() {
            const data_url = network.canvas.getContext().canvas.toDataURL("image/png");
            const a = document.createElement("a");
            a.href = data_url;
            a.download = `genealogy-tree-${livestock_filter.get_value()}.png`;
            a.click();
        }
        function export_network_as_jpg() {
            const data_url = network.canvas.getContext().canvas.toDataURL("image/jpeg");
            const a = document.createElement("a");
            a.href = data_url;
            a.download = `genealogy-tree-${livestock_filter.get_value()}.jpg`;
            a.click();
        }
        function export_network_as_csv() {
            const headers = ["ID", "Name", "Gender", "Sire_ID", "Dam_ID"];
            let csv_data = current_nodes_data.map(node => {
                if (node.id.startsWith('p-')) return null;
                return [
                    node.id,
                    `"${(node.label || '').replace(/"/g, '""')}"`,
                    node.group || "",
                    node.sire_father || "",
                    node.dam_mother || ""
                ];
            }).filter(row => row);

            let csv_content = [headers.join(","), ...csv_data.map(row => row.join(","))].join("\r\n");

            const encoded_uri = 'data:text/csv;charset=utf-8,' + encodeURI(csv_content);
            const link = document.createElement("a");
            link.setAttribute("href", encoded_uri);
            link.setAttribute("download", `genealogy-data-${livestock_filter.get_value()}.csv`);
            document.body.appendChild(link);
            link.click();
            document.body.removeChild(link);
        }
    });
};