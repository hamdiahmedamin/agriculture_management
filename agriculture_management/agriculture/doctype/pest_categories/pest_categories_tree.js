frappe.provide("frappe.treeview_settings");
frappe.provide('frappe.views.trees');

frappe.treeview_settings['Pest Categories'] = {
    breadcrumb: 'Agriculture',
    title: 'Pest Categories',
    // fields for a new node
    fields: [{
        fieldtype: 'Data',
        fieldname: 'pest_category_name',
        label: 'Pest Category Name',
        reqd: true
    }],
    on_change: function () {},
    // ignore fields even if mandatory
    //ignore_fields: ['parent_account'],
    // to add custom buttons under 3-dot menu group
    onload: function (treeview) {
        // triggered when tree view is instanciated
    },
    post_render: function (treeview) {
        // triggered when tree is instanciated
    },
    onrender: function (node) {
        // triggered when a node is instanciated
        if (frappe.boot.user.can_read.indexOf("Pest Categories") == -1) return;
    },
    on_get_node: function (nodes) {
        // triggered when `get_tree_nodes` returns nodes
        if (frappe.boot.user.can_read.indexOf("Pest Categories") == -1) return;

    },
    // custom buttons to be displayed beside each node
    toolbar: [{
        label: __("Add Child"),
        condition: function (node) {
            if (!node.is_root) {
                frappe.db.get_value("Pest Categories", node.data.value, "is_main")
                    .then((r) => {
                        if (!r.message.is_main) {
                            return node.expandable && !node.hide_add && !r.message.is_main;
                        }
                    })
                    return true;
            }

        },
        click: function () {
            var me = frappe.views.trees['Pest Categories'];
            me.new_node();
            console.log(me);

        },
        btnClass: 'hidden-xs'
    }],
    // enable custom buttons beside each node
    extend_toolbar: true,
}