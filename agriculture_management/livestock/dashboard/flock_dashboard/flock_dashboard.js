frappe.provide('agriculture.livestock');

agriculture.livestock.FlockDashboard = class FlockDashboard {
    constructor(opts) {
        Object.assign(this, opts);
        this.make();
    }

    make() {
        this.wrapper = $(this.parent);
        this.body = $('<div>').appendTo(this.wrapper);
    }

    refresh() {
        if (!this.flock_name) return;

        frappe.call({
            method: 'agriculture_management.livestock.dashboard.flock_dashboard.flock_dashboard.get_data',
            args: {
                flock_name: this.flock_name
            }
        }).then((r) => {
            this.render(r.message);
        });
    }

    render(data) {
        this.body.empty();
        if (data && data.warehouse) {
            this.body.html(frappe.render_template('flock_dashboard', data));
        } else {
            this.body.html(`<div class="text-muted" style="padding: 15px;">
                ${__("No stock information available for this flock.")}
            </div>`);
        }
    }
}