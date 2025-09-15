(() => {
  // ../agriculture_management/agriculture_management/livestock/dashboard/flock_dashboard/flock_dashboard.js
  frappe.provide("agriculture.livestock");
  agriculture.livestock.FlockDashboard = class FlockDashboard {
    constructor(opts) {
      Object.assign(this, opts);
      this.make();
    }
    make() {
      this.wrapper = $(this.parent);
      this.body = $("<div>").appendTo(this.wrapper);
    }
    refresh() {
      if (!this.flock_name)
        return;
      frappe.call({
        method: "agriculture_management.livestock.dashboard.flock_dashboard.flock_dashboard.get_data",
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
        this.body.html(frappe.render_template("flock_dashboard", data));
      } else {
        this.body.html(`<div class="text-muted" style="padding: 15px;">
                ${__("No stock information available for this flock.")}
            </div>`);
      }
    }
  };

  // frappe-html:/home/aminos/dokos-bench/apps/agriculture_management/agriculture_management/livestock/dashboard/flock_dashboard/flock_dashboard.html
  frappe.templates["flock_dashboard"] = `<div class="flock-stock-level">
    <div class="row">
        <div class="col-sm-6 text-muted">Current Warehouse:</div>
        <div class="col-sm-6">
            <a href="/app/warehouse/{{ warehouse }}">{{ warehouse }}</a>
        </div>
    </div>
    <div class="row">
        <div class="col-sm-6 text-muted">Live Stock Count:</div>
        <div class="col-sm-6">
            <strong>{{ actual_qty }} {{ stock_uom }}</strong>
        </div>
    </div>
</div>

<style>
    .flock-stock-level {
        padding: var(--padding-sm);
        font-size: var(--text-md);
    }
    .flock-stock-level .row {
        margin-bottom: var(--margin-xs);
    }
</style>`;
})();
//# sourceMappingURL=flock_dashboard.bundle.RQKVUDW4.js.map
