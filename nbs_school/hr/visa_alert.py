import frappe
from frappe import _
from frappe.utils import date_diff, today

# Threshold constants (in days)
THRESHOLD_YELLOW = 60
THRESHOLD_ORANGE = 30
THRESHOLD_RED = 14
THRESHOLD_CRITICAL = 7


def _get_alert_level(days: int) -> tuple:
    """
    Determine the alert level based on remaining days.

    Args:
        days: Number of days until expiry (can be negative for already expired).

    Returns:
        tuple of (level: str, hex_color: str, message: str).
    """
    if days <= 0:
        return ("expired", "#742a2a", "EXPIRED")
    if days < THRESHOLD_RED:
        return ("critical", "#c53030", "CRITICAL")
    if days < THRESHOLD_ORANGE:
        return ("red", "#e53e3e", "Urgent")
    if days < THRESHOLD_YELLOW:
        return ("orange", "#ed8936", "Within 30 days")
    return ("yellow", "#ecc94b", "Expiring soon")


def check_visa_expiry_daily():
    """
    Daily scheduled task that checks all active Employees for visa/contract
    expiry and creates ToDo alerts for the HR Manager.

    Thresholds:
        - >= 60 days: yellow (Expiring soon)
        - >= 30 days: orange (Within 30 days)
        - >= 14 days: red (Urgent)
        - < 14 days: critical (CRITICAL)
        - <= 0 days: expired (EXPIRED)

    Employees without a valid_upto date are skipped.
    """
    employees = frappe.get_all(
        "Employee",
        filters={
            "status": "Active",
            "valid_upto": ["!=", ""],
        },
        fields=["name", "employee_name", "valid_upto"],
    )

    today_date = today()

    for emp in employees:
        if not emp.valid_upto:
            continue

        remaining_days = date_diff(emp.valid_upto, today_date)
        level, _color, message = _get_alert_level(remaining_days)

        description = (
            f"Visa/Contract expiry alert: {emp.employee_name} ({emp.name})"
            f" expires {emp.valid_upto} — {message}"
        )

        try:
            frappe.get_doc(
                {
                    "doctype": "ToDo",
                    "allocated_to": "HR Manager",
                    "description": description,
                    "reference_type": "Employee",
                    "reference_name": emp.name,
                }
            ).insert(ignore_permissions=True)
        except Exception as e:
            frappe.log_error(
                message=f"Failed to create ToDo for Employee {emp.name}: {e}",
                title="NBS Visa Alert",
            )

    # Log a summary of the run
    expired_count = sum(
        1 for emp in employees if emp.valid_upto and date_diff(emp.valid_upto, today_date) <= 0
    )
    frappe.log_error(
        message=(
            f"Visa expiry check completed. "
            f"Total active employees checked: {len(employees)}. "
            f"Expired: {expired_count}."
        ),
        title="NBS Visa Alert Daily Run",
    )


@frappe.whitelist()
def get_visa_expiry_summary() -> dict:
    """
    Return a summary of visa/contract expiry status across all active employees.

    Returns:
        dict with counts per alert level and total active employees.
    """
    employees = frappe.get_all(
        "Employee",
        filters={
            "status": "Active",
            "valid_upto": ["!=", ""],
        },
        fields=["name", "valid_upto"],
    )

    today_date = today()
    counts = {
        "yellow": 0,
        "orange": 0,
        "red": 0,
        "critical": 0,
        "expired": 0,
    }

    for emp in employees:
        if not emp.valid_upto:
            continue

        remaining_days = date_diff(emp.valid_upto, today_date)
        level, _color, _message = _get_alert_level(remaining_days)

        if level in counts:
            counts[level] += 1

    counts["total_active"] = len(employees)
    return counts
