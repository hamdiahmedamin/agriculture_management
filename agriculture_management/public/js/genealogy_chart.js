// Use the 'livestock' namespace
frappe.provide("livestock");

livestock.GenealogyChart = class {
    constructor(doctype, page, wrapper, method) {
        this.doctype = doctype;
        this.page = page;
        this.wrapper = $(wrapper); // The div where the chart will be
        this.method = method;
        this.nodes = {}; // A map to store all created node objects by their ID

        this.page.main.css({ "min-height": "500px", "overflow": "auto" });
    }

    show(root_node_id) {
        this.root_node_id = root_node_id;
        this.make_chart_area();
        this.render_root_node();
    }

    make_chart_area() {
        // We only create the containers. The nodes will be added dynamically.
        this.wrapper.html(`
            <div id="hierarchy-chart" style="text-align: center;">
                <ul class="hierarchy" style="list-style-type: none; padding: 0;"></ul>
            </div>
        `);
        this.$hierarchy = this.wrapper.find('.hierarchy');
    }

    render_root_node() {
        frappe.db.get_doc(this.doctype, this.root_node_id).then(doc => {
            let root_data = {
                id: doc.name,
                name: doc.animal_name || doc.name,
                title: doc.gender,
                expandable: !!(doc.sire_father || doc.dam_mother)
            };

            // Create the first Node object
            let root_node = this.add_node(null, root_data);

            // DIRECTLY CALL the expand method instead of simulating a click
            if (root_node.expandable) {
                root_node.expand();
            }
        });
    }

    add_node(parent_id, data) {
        // Create a new instance of our inner Node class
        let node = new this.Node(data, this);
        this.nodes[data.id] = node;
        node.parent_id = parent_id;
        node.make_element(); // This will create and append the HTML
        return node;
    }
};

// Inner class for each node in the tree. This encapsulates its own logic.
livestock.GenealogyChart.prototype.Node = class {
    constructor(data, chart) {
        $.extend(this, data); // Copies id, name, title, expandable to 'this'
        this.chart = chart;
        this.expanded = false;
    }

    make_element() {
        let parent_ul;
        if (this.parent_id) {
            // Find the parent's <ul> container for children
            parent_ul = this.chart.nodes[this.parent_id].$children;
        } else {
            // This is the root node
            parent_ul = this.chart.$hierarchy;
        }

        let node_html = `
            <li class="child-node" style="display: inline-block; vertical-align: top; padding: 20px 5px 0 5px; position: relative;">
                <div class="node-card" id="${this.id}" style="border: 1px solid #ccc; padding: 10px; margin: 10px; border-radius: 4px; background: white; cursor: pointer;">
                    <div class="node-name" style="font-weight: bold;">${this.name}</div>
                    <div class="node-title text-muted">${this.title || ''}</div>
                    ${this.expandable ? `<div class="node-expand-btn" style="cursor: pointer; font-family: monospace; padding-top: 5px; color: #007bff;">[+]</div>` : ''}
                </div>
                <ul class="node-children" style="padding-top: 40px; position: relative; white-space: nowrap;"></ul>
            </li>
        `;

        this.$element = $(node_html).appendTo(parent_ul);
        this.$card = this.$element.find('.node-card');
        this.$children = this.$element.find('.node-children');

        this.bind_events();
    }

    bind_events() {
        this.$card.find('.node-expand-btn').on('click', (e) => {
            e.stopPropagation();
            this.toggle();
        });

        this.$card.on('click', (e) => {
            if (!$(e.target).hasClass('node-expand-btn')) {
                frappe.set_route("Form", this.chart.doctype, this.id);
            }
        });
    }

    toggle() {
        if (this.expanded) this.collapse();
        else this.expand();
    }

    expand() {
        if (!this.expandable || this.expanded) return;
        
        this.expanded = true;
        this.$card.find('.node-expand-btn').text('[-]');

        frappe.call({
            method: this.chart.method,
            args: { parent: this.id },
            callback: (r) => {
                if (r.message && r.message.length > 0) {
                    r.message.forEach(parent_data => {
                        this.chart.add_node(this.id, parent_data);
                    });
                } else {
                    this.expandable = false;
                    this.$card.find('.node-expand-btn').hide();
                }
            }
        });
    }

    collapse() {
        this.expanded = false;
        this.$children.empty();
        this.$card.find('.node-expand-btn').text('[+]');
    }
};