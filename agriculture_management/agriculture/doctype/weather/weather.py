# Copyright (c) 2017, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt


import frappe
import pyowm
from frappe.utils import today
from pyowm import OWM
from pyowm.utils import config
from pyowm.utils import timestamps
from frappe.model.document import Document
from frappe import _


class Weather(Document):

    @frappe.whitelist()
    def load_contents(self):

        docs = frappe.get_all("Agriculture Analysis Criteria", filters={
                              'linked_doctype': 'Weather'})
        for doc in docs:
            self.append('weather_parameter', {'title': str(doc.name), })
        self.date = today()

    @frappe.whitelist()
    def load_owm(self):
        lat = self.latitude
        lon = self.longitude

        owm_setting = frappe.get_single('OWM Setting')
        if (owm_setting.chk_enable):
            api_key = frappe.get_single('OWM Setting').api_key
            if bool(lat) == True and bool(lon) == True:
                owm = OWM(api_key)
                mgr = owm.weather_manager()
                one_call = mgr.one_call(lat, lon)
                temp_obs = one_call.forecast_daily[0].temperature(
                    'celsius').get('day', None)
                temp_min = one_call.forecast_daily[0].temperature(
                    'celsius').get('min', None)
                temp_max = one_call.forecast_daily[0].temperature(
                    'celsius').get('max', None)
                humidity = one_call.current.humidity
                docs = frappe.get_all('Agriculture Analysis Criteria', filters={
                    'linked_doctype': 'Weather'})
                for doc in docs:
                    match str(doc.name):
                        case "Degree Days":
                            value = (temp_min+temp_max)/2
                        case "Insolation/ PAR (Photosynthetically Active Radiation)":
                            value = one_call.current.uvi
                        case "Pressure":
                            value = one_call.forecast_daily[0].pressure
                        case "Humidity":
                            value = humidity
                        case "Precipitation Received":
                            value = one_call.current.rain
                        case "Dew Point":
                            value = temp_obs-((100-humidity)/5)
                        case "Temperature Average":
                            value = temp_obs
                        case "Temperature Low":
                            value = temp_min
                        case "Temperature High":
                            value = temp_max
                    self.append('weather_parameter', {
                                'title': str(doc.name), 'value': value, })
        else:
            frappe.msgprint(
                msg='OWM API Key disabled',
                title='Error'
            )
            return False
