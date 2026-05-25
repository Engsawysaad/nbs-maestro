import frappe
from frappe import _
from frappe.query_builder.functions import Sum
from frappe.utils import flt


def execute(filters=None):
	columns = get_columns()
	data = get_data(filters)
	return columns, data


def get_columns():
	return [
		{
			"fieldname": "account",
			"label": _("Account"),
			"fieldtype": "Link",
			"options": "Account",
			"width": 320,
		},
		{
			"fieldname": "type",
			"label": _("Type"),
			"fieldtype": "Data",
			"width": 110,
		},
		{
			"fieldname": "amount",
			"label": _("Amount (KWD)"),
			"fieldtype": "Currency",
			"options": "currency",
			"width": 150,
		},
		{
			"fieldname": "zakatable_amount",
			"label": _("Zakatable Amount (KWD)"),
			"fieldtype": "Currency",
			"options": "currency",
			"width": 180,
		},
		{
			"fieldname": "zakat_due",
			"label": _("Zakat Due (KWD)"),
			"fieldtype": "Currency",
			"options": "currency",
			"width": 150,
		},
	]


def get_data(filters):
	"""Compute Zakat (2.5 %) from P&L GL Entry data for a selected fiscal year."""
	try:
		if not filters or not filters.get("fiscal_year"):
			frappe.throw(_("Fiscal Year is mandatory"))

		fiscal_year = filters.get("fiscal_year")

		# ---------------------------------------------------------
		# 1. Aggregate P&L account balances from GL Entry
		# ---------------------------------------------------------
		gl_entry = frappe.qb.DocType("GL Entry")
		account = frappe.qb.DocType("Account")

		pl_data = (
			frappe.qb.from_(gl_entry)
			.inner_join(account)
			.on(gl_entry.account == account.name)
			.select(
				gl_entry.account,
				account.root_type.as_("root_type"),
				Sum(gl_entry.debit).as_("total_debit"),
				Sum(gl_entry.credit).as_("total_credit"),
			)
			.where(
				(gl_entry.fiscal_year == fiscal_year)
				& (gl_entry.is_cancelled == 0)
				& (account.report_type == "Profit and Loss")
				& (account.is_group == 0)
			)
			.groupby(gl_entry.account, account.root_type)
			.orderby(account.root_type, order="desc")
			.orderby(gl_entry.account)
		).run(as_dict=True)

		# ---------------------------------------------------------
		# 2. Build detail rows + compute totals
		# ---------------------------------------------------------
		rows = []
		total_income = 0.0
		total_expense = 0.0

		for entry in pl_data:
			if entry.root_type == "Income":
				balance = flt(entry.total_credit) - flt(entry.total_debit)
				total_income += balance
			else:
				balance = flt(entry.total_debit) - flt(entry.total_credit)
				total_expense += balance

			rows.append(
				{
					"account": entry.account,
					"type": _(entry.root_type),
					"amount": balance,
					"zakatable_amount": 0,
					"zakat_due": 0,
					"currency": "KWD",
				}
			)

		# ---------------------------------------------------------
		# 3. Compute Zakat
		# ---------------------------------------------------------
		net_profit = flt(total_income) - flt(total_expense)
		zakatable_base = max(0, net_profit)
		zakat_due = flt(zakatable_base * 0.025, 3)

		# ---------------------------------------------------------
		# 4. Summary rows
		# ---------------------------------------------------------
		rows.append({})
		rows.append(
			{
				"account": _("Total Income"),
				"type": "",
				"amount": total_income,
				"zakatable_amount": 0,
				"zakat_due": 0,
				"currency": "KWD",
			}
		)
		rows.append(
			{
				"account": _("Total Expenses"),
				"type": "",
				"amount": total_expense,
				"zakatable_amount": 0,
				"zakat_due": 0,
				"currency": "KWD",
			}
		)
		rows.append(
			{
				"account": _("Net Profit / (Loss)"),
				"type": "",
				"amount": net_profit,
				"zakatable_amount": 0,
				"zakat_due": 0,
				"currency": "KWD",
			}
		)
		rows.append(
			{
				"account": _("Zakatable Amount"),
				"type": "",
				"amount": 0,
				"zakatable_amount": zakatable_base,
				"zakat_due": 0,
				"currency": "KWD",
			}
		)
		rows.append(
			{
				"account": _("Zakat Due @ 2.5%"),
				"type": "",
				"amount": 0,
				"zakatable_amount": 0,
				"zakat_due": zakat_due,
				"currency": "KWD",
			}
		)

		# ---------------------------------------------------------
		# 5. Zakat Payable current balance (if account exists)
		# ---------------------------------------------------------
		zakat_payable = get_zakat_payable_balance(fiscal_year)
		rows.append(
			{
				"account": _("Zakat Payable (Current Balance)"),
				"type": "",
				"amount": zakat_payable,
				"zakatable_amount": 0,
				"zakat_due": 0,
				"currency": "KWD",
			}
		)

		return rows

	except Exception as e:
		frappe.log_error(
			message=f"Error in NBS Zakat Calculation Report: {e}",
			title="NBS Zakat Calculation Report Error",
		)
		return []


def get_zakat_payable_balance(fiscal_year):
	"""Return the credit balance of the Zakat Payable account for the fiscal year."""
	try:
		zakat_accounts = frappe.get_all(
			"Account",
			filters={
				"account_name": ["like", "%Zakat%"],
				"is_group": 0,
				"disabled": 0,
			},
			pluck="name",
			limit=1,
		)

		if not zakat_accounts:
			return 0

		gl_entry = frappe.qb.DocType("GL Entry")
		result = (
			frappe.qb.from_(gl_entry)
			.select(
				(Sum(gl_entry.credit) - Sum(gl_entry.debit)).as_("balance")
			)
			.where(
				(gl_entry.account == zakat_accounts[0])
				& (gl_entry.fiscal_year == fiscal_year)
				& (gl_entry.is_cancelled == 0)
			)
		).run(as_dict=True)

		return flt(result[0].balance) if result else 0

	except Exception:
		return 0
