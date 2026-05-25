import frappe

DOCUMENTS = [
    "Sales Invoice",
    "Payment Entry",
    "Journal Entry",
    "Employee",
    "Student",
]


def execute():
    """
    CUST-048: Enable Document Versioning (track_changes) on critical DocTypes.

    Enabling track_changes on these DocTypes allows users to view the
    document version history, see what changed between versions, and
    restore previous versions if needed.

    This is critical for:
    - Sales Invoice, Payment Entry, Journal Entry: Financial audit trail
    - Employee: HR record changes tracking
    - Student: Academic record changes tracking
    """
    enabled = 0
    errors = 0

    for dt in DOCUMENTS:
        try:
            frappe.db.set_value("DocType", dt, "track_changes", 1)
            enabled += 1
            frappe.log_error(
                message=f"Enabled track_changes on {dt}",
                title="NBS Versioning Enabled",
            )
        except Exception as e:
            errors += 1
            frappe.log_error(
                message=f"Failed to enable track_changes on {dt}: {e}",
                title="NBS Versioning Error",
            )

    frappe.log_error(
        message=f"Track changes enabled on {enabled}/{len(DOCUMENTS)} DocTypes ({errors} errors)",
        title="NBS Versioning Summary",
    )

    if errors:
        frappe.throw(
            f"NBS-048: {errors} error(s) enabling track_changes. Check Error Log."
        )
