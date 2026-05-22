import frappe
from frappe import _


def before_insert_set_email(doc, method):
    """
    CUST-024: Auto-generate placeholder email for Student on creation.

    Frappe v16 has a strict not-null constraint on `student_email_id`.
    If the Student record is being created without an email (common during
    data migration), this hook generates a placeholder to prevent the
    creation crash.

    The placeholder uses the student's ID/name as the local part:
    student_{id}@nbs.edu.kw

    Staff importing students should update real email addresses post-import.
    """
    if not doc.student_email_id:
        safe_id = frappe.db.get_value(
            "Student", filters={"student_email_id": ["is", "not set"]}, fieldname="name"
        )
        student_identifier = doc.get("title") or doc.get("student_name") or f"student-{doc.name}"
        # Create a URL-safe identifier
        safe_identifier = (
            student_identifier.lower()
            .replace(" ", "-")
            .replace("'", "")
            .replace("'", "")
            .replace(".", "")
            .strip("-")
        )
        generated_email = f"{safe_identifier}@nbs.edu.kw"

        # Ensure uniqueness
        counter = 0
        test_email = generated_email
        while frappe.get_value("Student", {"student_email_id": test_email}):
            counter += 1
            test_email = f"{safe_identifier}-{counter}@nbs.edu.kw"

        doc.student_email_id = test_email
        frappe.log_error(
            message=f"Auto-generated placeholder email {test_email} for Student {doc.name}",
            title="NBS Student Email Auto-Generated",
        )
