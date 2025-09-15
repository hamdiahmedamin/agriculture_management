/* eslint-disable */
// FINAL SCRIPT - Calling a dedicated server function for the lookup.
// in sanitization_log.js
frappe.ui.form.on('Sanitization Log', {
    refresh: function(frm) {
        // --- Button Visibility Logic ---
        // Show the button only for saved, draft documents that have a template selected.
        frm.toggle_display(
            'generate_tasks_button', 
            frm.doc.docstatus === 0 && !frm.is_new() && frm.doc.task_template
        );

        // --- Task Dashboard Rendering Logic ---
        // Only try to render the dashboard for saved documents.
        if (!frm.is_new()) {
            render_task_dashboard(frm);
        }
    },

    onload: function(frm) {
        // Filter the template to only show 'Sanitization' templates
        frm.set_query('task_template', function() {
            return {
                filters: {
                    'category': 'Sanitization',
                    'is_active': 1
                }
            };
        });
    },

    generate_tasks_button: function(frm) {
        frappe.call({
            method: 'agriculture_management.agriculture.api.generate_todos_from_template',
            args: {
                template_name: frm.doc.task_template,
                reference_doctype: frm.doc.doctype,
                reference_name: frm.doc.name
            },
            callback: function(r) {
                if (r.message) {
                    frappe.show_alert({
                        message: __(`Successfully generated ${r.message.count} ToDo(s). The list will now refresh.`),
                        indicator: 'green'
                    });
                    // After generating tasks, immediately refresh the dashboard to show them.
                    render_task_dashboard(frm);
                }
            }
        });
    }
});

frappe.ui.form.on('Sanitization Chemical', {
	/**
	 * This trigger fires when the 'sanitizing_agent' (the Item link) is changed.
	 */
	sanitizing_agent: function(frm, cdt, cdn) {
		let row = locals[cdt][cdn];

		if (row.sanitizing_agent) {
			
			let company = frm.doc.company || frappe.defaults.get_user_default("company");

			if (!company) {
				frappe.msgprint(__("Please set a Company on the form to fetch the default warehouse."));
				return;
			}
			
			// This is the new, robust method. We call our custom Python API function.
			frappe.call({
				method: 'agriculture_management.hydroponic.api.get_item_default_warehouse', // <-- IMPORTANT: Change 'your_custom_app'
				args: {
					item_code: row.sanitizing_agent,
					company: company
				},
				callback: function(r) {
					// The response 'r.message' will contain the warehouse name directly, or be empty.
					if (r.message) {
						// Set the value in our grid row.
						frappe.model.set_value(cdt, cdn, 'source_warehouse', r.message);
					}
				}
			});
		}
	}
});

/**
 * HELPER function to fetch and render the list of linked ToDos.
 * @param {object} frm - The current form object.
 */
function render_task_dashboard(frm) {
    // Find the HTML field (our container) and the dashboard wrapper
    const dashboard_field = frm.get_field("task_dashboard");
    const wrapper = dashboard_field.$wrapper;
    
    // Show a "Loading..." message
    wrapper.html('<div><p class="text-muted">Loading tasks...</p></div>');

    // Fetch the ToDo documents linked to this Sanitization Log
    frappe.db.get_list("ToDo", {
        filters: {
            reference_type: frm.doc.doctype,
            reference_name: frm.doc.name
        },
        fields: ["name", "description", "status", "allocated_to", "priority"],
        order_by: "creation asc"
    }).then(tasks => {
        // Start building the HTML string
        let html = `
            <div class="mb-3">
                <h5>Tasks for ${frm.doc.name}</h5>
            </div>
        `;

        if (tasks && tasks.length > 0) {
            html += '<ul class="list-group">';
            
            tasks.forEach(task => {
                let status_color = task.status === 'Open' ? 'warning' : 'success';
                let assigned_to_html = task.assigned_to ? 
                    `<span class="text-muted">| Allocated to: ${task.allocated_to}</span>` : '';

                html += `
                    <a href="/app/todo/${task.name}" class="list-group-item list-group-item-action">
                        <div class="d-flex w-100 justify-content-between">
                            <h6 class="mb-1">${task.description}</h6>
                            <span class="badge bg-${status_color}">${task.status}</span>
                        </div>
                        <small>Priority: ${task.priority || 'Medium'} ${assigned_to_html}</small>
                    </a>
                `;
            });

            html += '</ul>';
        } else {
            html += `
                <div class="text-muted p-4 text-center">
                    No tasks have been generated for this log.
                </div>
            `;
        }

        // Set the final generated HTML into the container
        wrapper.html(html);

        // Based on the number of tasks, we can show/hide the entire tab.
        frm.toggle_display('generated_tasks_tab', tasks && tasks.length > 0);

    });
}