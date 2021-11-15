from __future__ import unicode_literals
import frappe
from frappe.model.document import Document
from frappe.utils import getdate, now_datetime, nowdate, flt, cint, get_datetime_str, nowdate
from frappe import _
from erpnext.accounts.party import get_party_account
from erpnext.stock.get_item_details import get_item_details
import json
from frappe.utils.background_jobs import enqueue
from posawesome import console


@frappe.whitelist()
def get_items(price_list, posa_display_items_in_stock, warehouse, currency):
    price_list = price_list
    result = []

    items_data = frappe.db.sql("""
        SELECT
            name AS item_code,
            item_name,
            description,
            stock_uom,
            image,
            is_stock_item,
            has_variants,
            variant_of,
            item_group,
            idx as idx,
            has_batch_no,
            has_serial_no
        FROM
            `tabItem`
        WHERE
            disabled = 0
                AND is_sales_item = 1
                AND is_fixed_asset = 0

        ORDER BY
            name asc
            """, as_dict=1)

    if items_data:
        items = [d.item_code for d in items_data]
        item_prices_data = frappe.get_all("Item Price",
                                          fields=[
                                              "item_code", "price_list_rate", "currency"],
                                          filters={'price_list': price_list, 'item_code': ['in', items]})

        item_prices = {}
        for d in item_prices_data:
            item_prices[d.item_code] = d

        for item in items_data:
            item_code = item.item_code
            item_price = item_prices.get(item_code) or {}
            item_barcode = frappe.get_all("Item Barcode", filters={
                "parent": item_code}, fields=["barcode", "posa_uom"])
            item_stock_qty = get_stock_availability(item_code, warehouse)
            if posa_display_items_in_stock == 1:
                item_stock_qty = get_stock_availability(
                    item_code, warehouse)
            if posa_display_items_in_stock == 1 and (not item_stock_qty or item_stock_qty < 0):
                pass
            else:
                row = {}
                row.update(item)
                row.update({
                    'rate': item_price.get('price_list_rate') or 0,
                    'currency': item_price.get('currency') or currency,
                    'item_barcode': item_barcode or [],
                    'actual_qty': item_stock_qty or 0,
                })
                result.append(row)

    return result


def get_stock_availability(item_code, warehouse):
    latest_sle = frappe.db.sql("""select sum(actual_qty) as  actual_qty
		from `tabStock Ledger Entry` 
		where item_code = %s and warehouse = %s
		limit 1""", (item_code, warehouse), as_dict=1)

    sle_qty = latest_sle[0].actual_qty or 0 if latest_sle else 0
    return sle_qty

