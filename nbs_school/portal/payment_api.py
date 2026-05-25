import frappe
from frappe import _

@frappe.whitelist()
def initiate_payment(invoice_no, payment_method):
    """Initiate an online payment for a Sales Invoice."""
    try:
        if not frappe.db.exists("Sales Invoice", invoice_no):
            return {"success": False, "error": _("Invoice not found.")}

        invoice = frappe.get_doc("Sales Invoice", invoice_no)
        if invoice.docstatus != 1:
            return {"success": False, "error": _("Invoice is not submitted.")}

        if invoice.outstanding_amount <= 0:
            return {"success": False, "error": _("Invoice is already paid.")}

        outstanding = invoice.outstanding_amount
        student = invoice.student

        # Validate payment method
        valid_methods = ["KNET", "Credit Card", "Benefit Pay"]
        if payment_method not in valid_methods:
            return {"success": False, "error": _("Invalid payment method: {0}").format(payment_method)}

        # Resolve accounts
        company = invoice.company
        receivable_account = _get_receivable_account(company)
        bank_account = _get_bank_account(company)

        # Create Payment Entry (draft)
        timestamp = frappe.utils.now_datetime().strftime('%Y%m%d%H%M%S')
        pe = frappe.get_doc({
            "doctype": "Payment Entry",
            "payment_type": "Receive",
            "party_type": "Student",
            "party": student,
            "company": company,
            "paid_from": receivable_account,
            "paid_to": bank_account,
            "paid_amount": outstanding,
            "received_amount": outstanding,
            "reference_no": f"ONLINE-{invoice_no}-{timestamp}",
            "reference_date": frappe.utils.nowdate(),
            "mode_of_payment": payment_method,
            "remarks": _("Online payment via {0} for Invoice {1}").format(payment_method, invoice_no),
        })
        pe.insert(ignore_permissions=True)

        frappe.db.commit()

        return {
            "success": True,
            "payment_entry": pe.name,
            "redirect_url": f"/payment-confirmation/{pe.name}",
        }

    except Exception as e:
        frappe.log_error(
            message=f"Payment initiation failed for invoice {invoice_no}: {str(e)}",
            title="NBS Payment Initiation Error",
        )
        return {"success": False, "error": str(e)}


@frappe.whitelist()
def verify_payment(payment_entry_name):
    """Check the status of a Payment Entry."""
    try:
        if not frappe.db.exists("Payment Entry", payment_entry_name):
            return {"status": "not_found", "amount": 0, "invoice": ""}

        pe = frappe.get_doc("Payment Entry", payment_entry_name)
        status_map = {0: "pending", 1: "completed", 2: "cancelled"}
        return {
            "status": status_map.get(pe.docstatus, "unknown"),
            "amount": pe.paid_amount,
            "invoice": pe.reference_no,
        }
    except Exception as e:
        frappe.log_error(
            message=f"Payment verification error for {payment_entry_name}: {str(e)}",
            title="NBS Payment Verification Error",
        )
        return {"status": "error", "amount": 0, "invoice": "", "error": str(e)}


def _get_receivable_account(company):
    """Get the default receivable (debtors) account for the given company."""
    if not company:
        company = frappe.defaults.get_user_default("company")

    account = frappe.get_value("Company", company, "default_receivable_account")
    if account:
        return account

    frappe.throw(
        _("Default Receivable Account is not set for company {0}. Please set it in Company settings.").format(company)
    )


def _get_bank_account(company):
    """Get the default bank account for the given company."""
    if not company:
        company = frappe.defaults.get_user_default("company")

    # Try default bank account from Company
    account = frappe.get_value("Company", company, "default_bank_account")
    if account:
        return account

    # Fallback: find the first active Bank account in the company's chart
    account = frappe.db.get_value(
        "Account",
        {"company": company, "account_type": "Bank", "is_group": 0, "disabled": 0},
        "name",
        order_by="creation asc",
    )
    if account:
        return account

    frappe.throw(
        _("No Bank account found for company {0}. Please set a default bank account in Company settings.").format(company)
    )


@frappe.whitelist()
def get_payment_methods():
    """Return list of enabled payment methods."""
    return [
        {"id": "KNET", "label": "KNET"},
        {"id": "Credit Card", "label": _("Credit Card")},
        {"id": "Benefit Pay", "label": "Benefit Pay"},
    ]
