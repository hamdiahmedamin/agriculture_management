(()=>{frappe.provide("livestock");livestock.GenealogyChart=class{constructor(e,t,i,a){this.doctype=e,this.page=t,this.wrapper=$(i),this.method=a,this.nodes={},this.page.main.css({"min-height":"500px",overflow:"auto"})}show(e){this.root_node_id=e,this.make_chart_area(),this.render_root_node()}make_chart_area(){this.wrapper.html(`
            <div id="hierarchy-chart" style="text-align: center;">
                <ul class="hierarchy" style="list-style-type: none; padding: 0;"></ul>
            </div>
        `),this.$hierarchy=this.wrapper.find(".hierarchy")}render_root_node(){frappe.db.get_doc(this.doctype,this.root_node_id).then(e=>{let t={id:e.name,name:e.animal_name||e.name,title:e.gender,expandable:!!(e.sire_father||e.dam_mother)},i=this.add_node(null,t);i.expandable&&i.expand()})}add_node(e,t){let i=new this.Node(t,this);return this.nodes[t.id]=i,i.parent_id=e,i.make_element(),i}};livestock.GenealogyChart.prototype.Node=class{constructor(e,t){$.extend(this,e),this.chart=t,this.expanded=!1}make_element(){let e;this.parent_id?e=this.chart.nodes[this.parent_id].$children:e=this.chart.$hierarchy;let t=`
            <li class="child-node" style="display: inline-block; vertical-align: top; padding: 20px 5px 0 5px; position: relative;">
                <div class="node-card" id="${this.id}" style="border: 1px solid #ccc; padding: 10px; margin: 10px; border-radius: 4px; background: white; cursor: pointer;">
                    <div class="node-name" style="font-weight: bold;">${this.name}</div>
                    <div class="node-title text-muted">${this.title||""}</div>
                    ${this.expandable?'<div class="node-expand-btn" style="cursor: pointer; font-family: monospace; padding-top: 5px; color: #007bff;">[+]</div>':""}
                </div>
                <ul class="node-children" style="padding-top: 40px; position: relative; white-space: nowrap;"></ul>
            </li>
        `;this.$element=$(t).appendTo(e),this.$card=this.$element.find(".node-card"),this.$children=this.$element.find(".node-children"),this.bind_events()}bind_events(){this.$card.find(".node-expand-btn").on("click",e=>{e.stopPropagation(),this.toggle()}),this.$card.on("click",e=>{$(e.target).hasClass("node-expand-btn")||frappe.set_route("Form",this.chart.doctype,this.id)})}toggle(){this.expanded?this.collapse():this.expand()}expand(){!this.expandable||this.expanded||(this.expanded=!0,this.$card.find(".node-expand-btn").text("[-]"),frappe.call({method:this.chart.method,args:{parent:this.id},callback:e=>{e.message&&e.message.length>0?e.message.forEach(t=>{this.chart.add_node(this.id,t)}):(this.expandable=!1,this.$card.find(".node-expand-btn").hide())}}))}collapse(){this.expanded=!1,this.$children.empty(),this.$card.find(".node-expand-btn").text("[+]")}};})();
//# sourceMappingURL=genealogy-chart.bundle.ADGYH6GU.js.map
