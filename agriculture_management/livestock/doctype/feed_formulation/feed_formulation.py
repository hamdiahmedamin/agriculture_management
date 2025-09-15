# Copyright (c) 2025, aminos and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.utils import flt, getdate
from frappe import _


class FeedFormulation(Document):
    def validate(self):
        """
        On every save, this server-side hook calculates the definitive cost
        and validates the percentage using a backward-compatible method.
        """
        if not self.ingredients:
            self.total_percentage = 0
            self.total_formulation_cost = 0
            return

        total_percentage = 0
        total_cost = 0
        transaction_date = self.date or getdate()

        for row in self.ingredients:
            if not row.item:
                row.cost = 0
                continue

            # --- THIS IS THE DEFINITIVE, COMPATIBLE FIX ---
            # 1. Fetch all possible prices for the item and price list with a simple filter.
            possible_prices = frappe.get_all("Item Price",
                                             filters={
                                                 "item_code": row.item,
                                                 "price_list": self.buying_price_list
                                             },
                                             fields=["price_list_rate",
                                                     "valid_from", "valid_upto"]
                                             )

            rate = 0
            # 2. Filter the results by date in Python, which is 100% reliable.
            for price_record in possible_prices:
                is_valid_from = getdate(
                    price_record.valid_from) <= getdate(transaction_date)
                is_valid_upto = True
                if price_record.valid_upto:
                    if getdate(price_record.valid_upto) < getdate(transaction_date):
                        is_valid_upto = False

                if is_valid_from and is_valid_upto:
                    rate = flt(price_record.price_list_rate)
                    break  # We found the first valid price, so we stop.
            # --- END OF FIX ---

            # 3. Fallback to the item's valuation rate if no valid price was found.
            if not rate:
                rate = flt(frappe.db.get_value(
                    "Item", row.item, "valuation_rate"))

            row.cost = (flt(rate) * (flt(row.percentage) / 100))

            total_percentage += flt(row.percentage)
            total_cost += flt(row.cost)

        self.total_percentage = total_percentage
        self.total_formulation_cost = total_cost

        if abs(total_percentage - 100.0) > 0.001:
            frappe.throw(
                _("Total Percentage must be exactly 100%. Currently it is {0}%").format(
                    total_percentage),
                title=_("Invalid Percentage")
            )
