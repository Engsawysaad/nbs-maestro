import frappe
from frappe import _
from frappe.utils import today, add_days


def apply_late_fees_daily():
    """
    CUST-028: Late fee calculation — daily scheduled job.

    Runs daily to check all overdue Sales Invoices past the grace period
    (default: 5 days past due date) and applies a late fee (default: 1%
    of overdue amount per month pro-rated daily).

    Late fees are posted via a separate negative Sales Invoice line item
    using the configured Late Fee Income Account.
    """
    grace_days = frappe.db.get_single_value(
        "Education Settings", "late_fee_grace_days"
    ) or 5
    late_fee_rate = (
        frappe.db.get_single_value("Education Settings", "late_fee_rate") or 1.0
    )
    late_fee_account = frappe.db.get_single_value(
        "Education Settings", "late_fee_income_account"
    )

    cutoff_date = add_days(today(), -grace_days)

    overdue_invoices = frappe.get_all(
        "Sales Invoice",
        filters={
            "docstatus": 1,
            "status": ["in", ["Overdue", "Unpaid", "Partly Paid"]],
            "due_date": ["<=", cutoff_date],
            "outstanding_amount": [">", 0],
        },
        fields=[
            "name",
            "outstanding_amount",
            "due_date",
            "customer",
            "company",
        ],
    )

    if not overdue_invoices:
        return

    processed = 0
    errors = 0

    for inv in overdue_invoices:
        try:
            _apply_single_late_fee(inv, late_fee_rate, late_fee_account)
            processed += 1
        except Exception as e:
            errors += 1
            frappe.log_error(
                message=f"Failed to apply late fee for invoice {inv.name}: {e}",
                title="NBS Late Fee Application Error",
            )

    frappe.log_error(
        message=f"Late fee processing: {processed} fees applied, {errors} errors",
        title="NBS Late Fee Summary",
    )


def _apply_single_late_fee(invoice, rate, income_account):
    """Apply a late fee to a single overdue invoice."""
    # Calculate days overdue
    from datetime import datetime

    due_date = invoice.due_date
    if not due_date:
        return

    try:
        if isinstance(due_date, str):
            due_date_dt = datetime.strptime(str(due_date), "%Y-%m-%d")
        else:
            due_date_dt = due_date

        current_dt = datetime.now()
        days_overdue = (current_dt - due_date_dt).days
    except (ValueError, TypeError):
        return

    if days_overdue <= 0:
        return

    # Monthly rate pro-rated: rate * (days_overdue / 30)
    effective_rate = rate * (days_overdue / 30.0)
    if effective_rate > rate * 3:  # Cap at 3 months equivalent
        effective_rate = rate * 3

    late_fee_amount = invoice.outstanding_amount * (effective_rate / 100.0)
    if late_fee_amount <= 0:
        return

    # Create a new Sales Invoice for the late fee
    company_defaults = frappe.get_cached_doc("Company", invoice.company)

    late_fee_invoice = frappe.get_doc(
        {
            "doctype": "Sales Invoice",
            "customer": invoice.customer,
            "due_date": today(),
            "naming_series": "NBS-INV-",
            "items": [
                {
                    "item_name": _("Late Fee ({0} days overdue)").format(days_overdue),
                    "description": _(
                        "Late fee at {0}% on overdue amount {1} for invoice {2}"
                    ).format(effective_rate, invoice.outstanding_amount, invoice.name),
                    "qty": 1,
                    "rate": late_fee_amount,
                    "income_account": income_account
                    or company_defaults.default_income_account,
                }
            ],
        }
    )

    late_fee_invoice.set_missing_values()
    late_fee_invoice.insert(ignore_permissions=True)
    late_fee_invoice.submit()

    # Link late fee to original invoice via custom field or notes
    frappe.log_error(
        message=f"Late fee {late_fee_invoice.name} of {late_fee_amount} applied to invoice {invoice.name} ({days_overdue} days overdue)",
        title="NBS Late Fee Applied",
    )
