frappe.listview_settings['Hydroponic Crop Cycle'] = {
    get_indicator(doc) {
            // customize indicator color
            if (doc.status=="Active") {
                return [__("Active"), "cyan", "status,=,Active"];
            } else if (doc.status=="Planted") {
                return [__("Planted"), "green", "status,=,Planted"];
            }else if (doc.status=="Harvested") {
                return [__("Harvested"), "green", "status,=,Harvested"];
            }else if (doc.status=="Completed") {
                return [__("Completed"), "blue", "status,=,Completed"];
            }else if (doc.status=="Failed") {
                return [__("Failed"), "red", "status,=,Failed"];
            }else{
                return [__("Upcoming"), "purple", "status,=,Upcoming"];
            }
        },
    }