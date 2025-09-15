frappe.provide('agriculture');

agriculture.TernaryPlot = class TernaryPlot {
	constructor(opts) {
		Object.assign(this, opts);

		frappe.require('assets/agriculture_management/js/snap.svg-min.js', () => {
			this.make_svg();
			this.init_snap();
			this.init_config();
			this.make_plot();
			this.make_plot_marking();
			this.make_legend();
			this.mark_blip();
		});
	}

	make_svg() {
		this.$svg = $('<svg height="350" width="400">');
		$(this.parent).append(this.$svg);
	}

	init_snap() {
		this.paper = new Snap(this.$svg.get(0));
	}

	init_config() {
		this.config = {
			triangle_side: 300,
			spacing: 50,
			strokeWidth: 1,
			stroke: frappe.ui.color.get('black')
		};
		this.config.scaling_factor = this.config.triangle_side / 100;
		let { triangle_side: t, spacing: s, scaling_factor: p } = this.config;

		this.coords = {
			sand: {
				points: [
					s + t * Snap.cos(60), s,
					s, s + t * Snap.cos(30),
					s + t, s + t * Snap.cos(30)
				],
				color: frappe.ui.color.get('#F4E1A1')
			},
			loamy_sand: {
				points: [
					s + 15 * p * Snap.cos(60), s + (100 - 15) * p * Snap.cos(30),
					s + 10 * p * Snap.cos(60), s + (100 - 10) * p * Snap.cos(30),
					s + (100 - 85) * p, s + t * Snap.cos(30),
					s + (100 - 70) * p, s + t * Snap.cos(30)
				],
				color: frappe.ui.color.get('#EFD9B4')
			},
			sandy_loam: {
				points: [
					s + 20 * p * Snap.cos(60) + 27.5 * p, s + (100 - 20) * p * Snap.cos(30),
					s + 20 * p * Snap.cos(60), s + (100 - 20) * p * Snap.cos(30),
					s + 15 * p * Snap.cos(60), s + (100 - 15) * p * Snap.cos(30),
					s + (100 - 75) * p, s + t * Snap.cos(30),
					s + (100 - 50) * p, s + t * Snap.cos(30),
					s + (100 - 50) * p + 7.5 * p * Snap.cos(60), s + t * Snap.cos(30) - 7.5 * p * Snap.cos(30),
					s + (100 - 50) * p + 7.5 * p * Snap.cos(60) - 10 * p, s + t * Snap.cos(30) - 7.5 * p * Snap.cos(30)
				],
				color: frappe.ui.color.get('#E6C88A')
			},
			loam: {
				points: [
					s + (100 - 50) * p + 27.5 * p * Snap.cos(60), s + t * Snap.cos(30) - 27.5 * p * Snap.cos(30),
					s + (100 - 50) * p + 27.5 * p * Snap.cos(60) - 22.5 * p, s + t * Snap.cos(30) - 27.5 * p * Snap.cos(30),
					s + 20 * p * Snap.cos(60) + 27.5 * p, s + (100 - 20) * p * Snap.cos(30),
					s + (100 - 50) * p + 7.5 * p * Snap.cos(60) - 10 * p, s + t * Snap.cos(30) - 7.5 * p * Snap.cos(30),
					s + (100 - 50) * p + 7.5 * p * Snap.cos(60), s + t * Snap.cos(30) - 7.5 * p * Snap.cos(30)
				],
				color: frappe.ui.color.get('#C19A6B')
			},
			silt_loam: {
				points: [
					s + t - 27.5 * p * Snap.cos(60), s + 72.5 * p * Snap.cos(30),
					s + (100 - 50) * p + 27.5 * p * Snap.cos(60), s + t * Snap.cos(30) - 27.5 * p * Snap.cos(30),
					s + (100 - 50) * p, s + t * Snap.cos(30),
					s + (100 - 20) * p, s + t * Snap.cos(30),
					s + (100 - 20) * p + 12.5 * p * Snap.cos(60), s + 90 * p * Snap.cos(30),
					s + t - 12.5 * p * Snap.cos(60), s + (100 - 12.5) * p * Snap.cos(30)
				],
				color: frappe.ui.color.get('#D2C6B2')
			},
			silt: {
				points: [
					s + t - 12.5 * p * Snap.cos(60), s + (100 - 12.5) * p * Snap.cos(30),
					s + (100 - 20) * p + 12.5 * p * Snap.cos(60), s + 90 * p * Snap.cos(30),
					s + (100 - 20) * p, s + t * Snap.cos(30),
					s + t, s + t * Snap.cos(30)
				],
				color: frappe.ui.color.get('#CFCFC4')
			},
			silty_clay_loam: {
				points: [
					s + t - 40 * p * Snap.cos(60), s + 60 * p * Snap.cos(30),
					s + t - 40 * p * Snap.cos(60) - 20 * p, s + 60 * p * Snap.cos(30),
					s + t - 27.5 * p * Snap.cos(60) - 20 * p, s + 72.5 * p * Snap.cos(30),
					s + t - 27.5 * p * Snap.cos(60), s + 72.5 * p * Snap.cos(30)
				],
				color: frappe.ui.color.get('#A58E74')
			},
			silty_clay: {
				points: [
					s + t - 60 * p * Snap.cos(60), s + 40 * p * Snap.cos(30),
					s + t - 40 * p * Snap.cos(60) - 20 * p, s + 60 * p * Snap.cos(30),
					s + t - 40 * p * Snap.cos(60), s + 60 * p * Snap.cos(30)
				],
				color: frappe.ui.color.get('#8C7E77')
			},
			clay_loam: {
				points: [
					s + t - 40 * p * Snap.cos(60) - 20 * p, s + 60 * p * Snap.cos(30),
					s + t - 40 * p * Snap.cos(60) - 45 * p, s + 60 * p * Snap.cos(30),
					s + t - 27.5 * p * Snap.cos(60) - 45 * p, s + 72.5 * p * Snap.cos(30),
					s + t - 27.5 * p * Snap.cos(60) - 20 * p, s + 72.5 * p * Snap.cos(30)
				],
				color: frappe.ui.color.get('#A9745B')
			},
			sandy_clay_loam: {
				points: [
					s + 35 * p * Snap.cos(60) + 20 * p, s + (100 - 35) * p * Snap.cos(30),
					s + 35 * p * Snap.cos(60), s + (100 - 35) * p * Snap.cos(30),
					s + 20 * p * Snap.cos(60), s + (100 - 20) * p * Snap.cos(30),
					s + 20 * p * Snap.cos(60) + 27.5 * p, s + (100 - 20) * p * Snap.cos(30),
					s + t - 27.5 * p * Snap.cos(60) - 45 * p, s + 72.5 * p * Snap.cos(30)
				],
				color: frappe.ui.color.get('#B6866F')
			},
			sandy_clay: {
				points: [
					s + 55 * p * Snap.cos(60), s + (100 - 55) * p * Snap.cos(30),
					s + 35 * p * Snap.cos(60), s + (100 - 35) * p * Snap.cos(30),
					s + 35 * p * Snap.cos(60) + 20 * p, s + (100 - 35) * p * Snap.cos(30)
				],
				color: frappe.ui.color.get('#9E5A3C')
			},
			clay: {
				points: [
					s + t * Snap.cos(60), s,
					s + 55 * p * Snap.cos(60), s + (100 - 55) * p * Snap.cos(30),
					s + t - 40 * p * Snap.cos(60) - 45 * p, s + 60 * p * Snap.cos(30),
					s + t - 40 * p * Snap.cos(60) - 20 * p, s + 60 * p * Snap.cos(30),
					s + t - 60 * p * Snap.cos(60), s + 40 * p * Snap.cos(30)
				],
				color: frappe.ui.color.get('#7A3E2E')
			},
		};
	}

	get_coords(soil_type) {
		return this.coords[soil_type].points;
	}

	get_color(soil_type) {
		return this.coords[soil_type].color;
	}

	make_plot() {
		for (let soil_type in this.coords) {
			this.paper.polygon(this.get_coords(soil_type)).attr({
				fill: this.get_color(soil_type),
				stroke: this.config.stroke,
				strokeWidth: this.config.strokeWidth
			});
		}
	}

	make_plot_marking() {
		let { triangle_side: t, spacing: s, scaling_factor: p } = this.config;

		let clay = this.paper.text(t * Snap.cos(60) / 2, s + t * Snap.cos(30) / 2, __("Clay")).attr({
			fill: frappe.ui.color.get('black')
		});
		clay.transform("r300");

		let silt = this.paper.text(t, s + t * Snap.cos(30) / 2, __("Silt")).attr({
			fill: frappe.ui.color.get('black')
		});
		silt.transform("r60");

		let sand = this.paper.text(35 + t * Snap.cos(60), 90 + t * Snap.cos(30), __("Sand")).attr({
			fill: frappe.ui.color.get('black')
		});
		sand.transform("r0");
	}

	make_legend() {
		// Helper function to convert a key like 'sandy_loam' to 'Sandy Loam'
		const format_title = (key) => {
			let words = key.split('_');
			words = words.map(word => word.charAt(0).toUpperCase() + word.slice(1));
			return words.join(' ');
		};

		let index = 1;
		let offset = 0;
		let exec_once = true;

		for (let soil_type in this.coords) {
			if (index > 6 && exec_once){
				offset = 300;
				index = 1;
				exec_once = false;
			}
			
			// Draw the colored rectangle for the legend item
			let rect = this.paper.rect(0 + offset, 0 + index * 20, 100, 19, 5, 5).attr({
				fill: this.get_color(soil_type),
				stroke: frappe.ui.color.get('black')
			});

			// --- THIS IS THE FIX ---
			// Use our new helper function to create a clean title
			let legend_title = format_title(soil_type);
			
			// Draw the text with the clean title
			let text = this.paper.text(5 + offset, 16 + index * 20, legend_title).attr({
				fill: frappe.ui.color.get('black'),
				'font-size': 12
			});
			index++;
		}
	}

	mark_blip({clay, sand, silt} = this) {
		if (clay + sand + silt != 0){
			let { triangle_side: t, spacing: s, scaling_factor: p } = this.config;

			let x_blip = s + clay * p * Snap.cos(60) + silt * p;
			let y_blip = s + silt * p * Snap.cos(30) + sand * p * Snap.sin(60);
			this.blip = this.paper.circle(x_blip, y_blip, 4).attr({
				fill: frappe.ui.color.get("orange"),
				stroke: frappe.ui.color.get("orange"),
				strokeWidth: 2
			});
		}
	}

	remove_blip() {
		if (typeof this.blip !== 'undefined')
			this.blip.remove();
	}
};
