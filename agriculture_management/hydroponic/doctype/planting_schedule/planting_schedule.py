# Copyright (c) 2025, aminos and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.utils import getdate

class PlantingSchedule(Document):
	def validate(self):
		"""
		This hook runs before saving to validate the document's data.
		"""
		self.validate_dates()
		self.validate_system_availability()

	def validate_dates(self):
		"""Ensures that the estimated harvest date is after the planting date."""
		if self.estimated_harvest_date and self.target_planting_date:
			if getdate(self.estimated_harvest_date) <= getdate(self.target_planting_date):
				frappe.throw("Estimated Harvest Date must be after the Target Planting Date.")
	
	def validate_system_availability(self):
		"""
		Checks if the selected Hydroponic System is already scheduled for another crop
		during the same overlapping period. This prevents double-booking.
		"""
		if not self.hydroponic_system or not self.target_planting_date or not self.estimated_harvest_date:
			return

		# Find other schedules that are NOT this one and NOT cancelled
		overlapping_schedules = frappe.db.get_all(
			"Planting Schedule",
			filters={
				"name": ["!=", self.name],
				"hydroponic_system": self.hydroponic_system,
				"status": ["!=", "Cancelled"],
				"target_planting_date": ["<", self.estimated_harvest_date],
				"estimated_harvest_date": [">", self.target_planting_date]
			},
			pluck="name"
		)

		if overlapping_schedules:
			frappe.throw(
				f"The selected Hydroponic System is already booked for this period by Planting Schedule(s): {', '.join(overlapping_schedules)}"
			)