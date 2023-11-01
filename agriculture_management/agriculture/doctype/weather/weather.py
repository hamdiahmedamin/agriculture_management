# Copyright (c) 2017, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt


import frappe
import pyowm
from pyowm import OWM
from pyowm.utils import config
from pyowm.utils import timestamps
from frappe.model.document import Document


class Weather(Document):

    @frappe.whitelist()
    def load_contents(self):
        docs = frappe.get_all("Agriculture Analysis Criteria", filters={'linked_doctype':'Weather'})
        for doc in docs:
            self.append('weather_parameter', {'title': str(doc.name),})
    
    @frappe.whitelist()
    def set_weather(self):
        owm = OWM('81b09706b0075c212be5ebfb9d69a915')
        mgr = owm.weather_manager()
        observation = mgr.weather_at_place('London,GB')
        docs = frappe.get_all("Agriculture Analysis Criteria", filters={'linked_doctype':'Weather'})
        for doc in docs:            
            match str(doc.name):
                case "Degree Days":
                    value = observation.weather.humidity
                case "Insolation/ PAR (Photosynthetically Active Radiation}":
                    value = observation.weather.humidity
                case "Pressure":
                    value = observation.weather.humidity
                case "Humidity":
                    value = observation.weather.humidity
                case "Precipitation Received":
                    value = observation.weather.humidity
                case "Dew Point":
                    value = observation.weather.humidity
                case "Temperature Average":
                    value = observation.weather.humidity
                case "Temperature Low":
                    value = observation.weather.humidity
                case "Temperature High":
                    value = observation.weather.humidity 
            self.append('weather_parameter', {'title': str(doc.name),'value': value,})
        

def switch(name):
    if name == "JavaScript":
        return "You can become a web developer."
    elif name == "PHP":
        return "You can become a backend developer."
    elif name == "Python":				
        return "You can become a Data Scientist"
    elif name == "Solidity":
        return "You can become a Blockchain developer."
    elif name == "Java":
        return "You can become a mobile app developer"