import frappe
from frappe import _
from frappe.utils import today, getdate, add_days


def generate_termly_fee_invoices():
    """
    CUST-026: Termly fee invoice auto-generation scheduler.

    Scheduled job (to run at term start via hooks.py scheduler_events).
    For all active Program Enrollments with a linked Fee Structure:
    1. Creates a Fee Schedule for the term
    2. Creates Sales Invoices from the Fee Schedule

    This function expects the following standard ERPNext Education
    DocTypes to be configured: Fee Structure, Fee Schedule, Program
    Enrollment, Sales Invoice.
    """
    active_enrollments = frappe.get_all(
        "Program Enrollment",
        filters={
            "docstatus": 1,
            "academic_term": _get_current_academic_term(),
        },
        fields=["name", "student", "program", "student_name"],
    )

    if not active_enrollments:
        frappe.log_error(
            message="No active Program Enrollments found for fee invoicing",
            title="NBS Fee Invoicing: No Enrollments",
        )
        return

    invoices_created = 0
    errors = 0

    for enrollment in active_enrollments:
        try:
            _process_enrollment_fee(enrollment)
            invoices_created += 1
        except Exception as e:
            errors += 1
            frappe.log_error(
                message=f"Failed to process fee for enrollment {enrollment.name} (Student: {enrollment.student}): {e}",
                title="NBS Fee Invoicing Error",
            )

    frappe.log_error(
        message=f"Fee invoicing complete: {invoices_created} invoices created, {errors} errors",
        title="NBS Fee Invoicing Summary",
    )


def _get_current_academic_term():
    """Get the active academic term."""
    current_term = frappe.get_all(
        "Academic Term",
        filters={
            "start_date": ["<=", today()],
            "end_date": [">=", today()],
        },
        limit=1,
    )
    if current_term:
        return current_term[0].name
    return None


def _process_enrollment_fee(enrollment):
    """Create Fee Schedule and Sales Invoice for a single enrollment."""
    fee_structure = frappe.get_value(
        "Program Enrollment", enrollment.name, "fee_structure"
    )
    if not fee_structure:
        return

    # Create Fee Schedule
    fee_schedule = frappe.get_doc(
        {
            "doctype": "Fee Schedule",
            "program": enrollment.program,
            "student": enrollment.student,
            "student_name": enrollment.student_name,
            "fee_structure": fee_structure,
            "due_date": add_days(today(), 30),  # 30 days from now
        }
    )
    fee_schedule.insert(ignore_permissions=True)

    # Create Sales Invoice from Fee Schedule
    _create_invoice_from_fee_schedule(fee_schedule.name, enrollment)


def _create_invoice_from_fee_schedule(fee_schedule_name, enrollment):
    """Generate a Sales Invoice from a Fee Schedule."""
    fee_schedule = frappe.get_doc("Fee Schedule", fee_schedule_name)
    fee_structure = frappe.get_doc("Fee Structure", fee_schedule.fee_structure)

    if not fee_structure.components:
        return

    invoice = frappe.get_doc(
        {
            "doctype": "Sales Invoice",
            "customer": enrollment.student,  # Student as customer; may need mapping
            "due_date": fee_schedule.due_date,
            "naming_series": "NBS-INV-",
            "items": [],
        }
    )

    for component in fee_structure.components:
        invoice.append(
            "items",
            {
                "item_name": component.fees_category,
                "description": _(f"{component.fees_category} - {enrollment.program}"),
                "qty": 1,
                "rate": component.amount,
                "income_account": component.get("income_account")
                or frappe.get_value(
                    "Company", frappe.defaults.get_global_default("company"), "default_income_account"
                ),
            },
        )

    invoice.set_missing_values()
    invoice.insert(ignore_permissions=True)
    invoice.submit()
