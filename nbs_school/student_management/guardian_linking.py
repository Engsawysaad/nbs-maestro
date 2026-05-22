import frappe
from frappe import _
from frappe.utils import nowdate


def on_update_auto_link_guardian(doc, method):
    """
    CUST-014: Guardian-Student linking automation.

    Triggered on Student `on_update`. If the Student has a guardian_email
    field populated, auto-links to an existing Guardian (matched by email)
    or creates a new Guardian record. Also sets User Permission so the
    Guardian can access the Student's documents.

    NOTE: Assumes a custom field `guardian_email` exists on Student DocType
    or uses the standard `student_email_id` as fallback.
    """
    guardian_email = doc.get("guardian_email") or doc.get("student_email_id")
    if not guardian_email:
        return

    guardian_name = _find_or_create_guardian(doc, guardian_email)
    if not guardian_name:
        return

    _link_guardian_to_student(guardian_name, doc.name)
    _set_guardian_user_permission(guardian_name, doc.name)


def _find_or_create_guardian(student_doc, email):
    """Find existing Guardian by email or create a new one."""
    existing = frappe.get_value("Guardian", {"email_address": email})
    if existing:
        return existing

    guardian_name = student_doc.get("guardian_name") or student_doc.get(
        "guardian_full_name"
    ) or email.split("@")[0]

    guardian = frappe.get_doc(
        {
            "doctype": "Guardian",
            "email_address": email,
            "guardian_name": guardian_name,
            "mobile_number": student_doc.get("guardian_mobile"),
            "guardian_phone": student_doc.get("guardian_mobile"),
        }
    )
    try:
        guardian.insert(ignore_permissions=True)
        frappe.log_error(
            message=f"Auto-created Guardian '{guardian.name}' for email {email}",
            title="NBS Guardian Auto-Create",
        )
        return guardian.name
    except Exception as e:
        frappe.log_error(
            message=f"Failed to create Guardian for email {email}: {e}",
            title="NBS Guardian Error",
        )
        return None


def _link_guardian_to_student(guardian_name, student_name):
    """Add Guardian-Student link if not already present."""
    existing = frappe.get_all(
        "Guardian Student",
        filters={"parent": guardian_name, "student": student_name},
        limit=1,
    )
    if existing:
        return

    try:
        guardian_doc = frappe.get_doc("Guardian", guardian_name)
        guardian_doc.append(
            "students",
            {
                "student": student_name,
            },
        )
        guardian_doc.save(ignore_permissions=True)
    except Exception as e:
        frappe.log_error(
            message=f"Failed to link Guardian {guardian_name} to Student {student_name}: {e}",
            title="NBS Guardian Link Error",
        )


def _set_guardian_user_permission(guardian_name, for_value, allow_doctype=None):
    """Set User Permission for the guardian to access the student."""
    guardian_email = frappe.get_value("Guardian", guardian_name, "email_address")
    if not guardian_email:
        return

    dt = allow_doctype or "Student"

    # Skip if the guardian has no User account yet — permission can be added
    # later when portal access is granted.
    if not frappe.db.exists("User", guardian_email):
        frappe.log_error(
            message=f"Skipped User Permission for {dt} {for_value}: no User exists for {guardian_email}",
            title="NBS Guardian User Permission Skipped",
        )
        return

    existing = frappe.get_all(
        "User Permission",
        filters={
            "allow": dt,
            "for_value": for_value,
            "user": guardian_email,
        },
        limit=1,
    )
    if existing:
        return

    perm = frappe.get_doc(
        {
            "doctype": "User Permission",
            "allow": dt,
            "for_value": for_value,
            "user": guardian_email,
            "apply_to_all_doctypes": 1,
        }
    )
    try:
        perm.insert(ignore_permissions=True)
    except Exception as e:
        frappe.log_error(
            message=f"Failed to create User Permission for {dt} {for_value} for {guardian_email}: {e}",
            title="NBS Guardian User Permission Error",
        )
