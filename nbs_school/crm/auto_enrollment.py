import frappe
from frappe import _


def on_update_opportunity_to_enrollment(doc, method):
    """
    CUST-038: CRM auto-enrollment pipeline.

    Triggered on Opportunity `on_update`. When Opportunity status changes
    to "Converted" (or a configured status), automatically:
    1. Creates a Student Applicant from the Opportunity data
    2. Converts to Student
    3. Creates a Program Enrollment

    This automates the CRM-to-Education pipeline so enrollment staff
    don't need to manually re-enter data.
    """
    convertible_statuses = ["Converted", "Closed as Converted"]
    if doc.status not in convertible_statuses:
        return

    # Check if already processed to prevent duplicates
    if frappe.get_all(
        "Student Applicant",
        filters={"custom_opportunity": doc.name},
        limit=1,
    ):
        return

    # Extract student/applicant details from Opportunity
    student_name = doc.contact_display or doc.organization or _("Unknown")
    email = None
    mobile = None

    # Try to get contact details
    if doc.contact_email:
        email = doc.contact_email
    elif doc.email_id:
        email = doc.email_id

    if doc.contact_mobile:
        mobile = doc.contact_mobile
    elif doc.mobile_no:
        mobile = doc.mobile_no

    # Get program from custom field or opportunity type
    program = doc.get("custom_program") or doc.get("opportunity_type")
    if not program:
        frappe.log_error(
            message=f"Opportunity {doc.name} has no program specified for enrollment",
            title="NBS CRM Auto-Enrollment: Missing Program",
        )
        return

    # 1. Create Student Applicant
    student_applicant = _create_student_applicant(
        doc, student_name, email, mobile, program
    )
    if not student_applicant:
        return

    # 2. Create or find Student record
    student = _find_or_create_student(student_applicant, email)
    if not student:
        return

    # 3. Create Program Enrollment
    _create_program_enrollment(doc, student, program)


def _create_student_applicant(opportunity, student_name, email, mobile, program):
    """Create a Student Applicant from Opportunity data."""
    applicant = frappe.get_doc(
        {
            "doctype": "Student Applicant",
            "title": student_name,
            "applicant_name": student_name,
            "email_address": email,
            "mobile_number": mobile,
            "program": program,
            "custom_opportunity": opportunity.name,
            "status": "Applied",
        }
    )
    try:
        applicant.insert(ignore_permissions=True)
        return applicant.name
    except Exception as e:
        frappe.log_error(
            message=f"Failed to create Student Applicant from Opportunity {opportunity.name}: {e}",
            title="NBS CRM Auto-Enrollment Error",
        )
        return None


def _find_or_create_student(applicant_name, email):
    """Find an existing Student by email or create from applicant."""
    if email:
        existing = frappe.get_value("Student", {"student_email_id": email})
        if existing:
            return existing

    applicant = frappe.get_doc("Student Applicant", applicant_name)

    student = frappe.get_doc(
        {
            "doctype": "Student",
            "student_name": applicant.applicant_name,
            "student_email_id": email or f"{applicant.name.lower()}@nbs.edu.kw",
            "mobile_number": applicant.mobile_number,
        }
    )
    try:
        student.insert(ignore_permissions=True)
        return student.name
    except Exception as e:
        frappe.log_error(
            message=f"Failed to create Student from applicant {applicant_name}: {e}",
            title="NBS CRM Auto-Enrollment Student Error",
        )
        return None


def _create_program_enrollment(opportunity, student, program):
    """Create a Program Enrollment for the student."""
    academic_term = frappe.get_all(
        "Academic Term",
        filters={
            "start_date": ["<=", frappe.utils.today()],
            "end_date": [">=", frappe.utils.today()],
        },
        limit=1,
    )

    enrollment = frappe.get_doc(
        {
            "doctype": "Program Enrollment",
            "student": student,
            "program": program,
            "academic_term": academic_term[0].name if academic_term else None,
            "enrollment_date": frappe.utils.today(),
        }
    )
    try:
        enrollment.insert(ignore_permissions=True)
        enrollment.submit()
        frappe.log_error(
            message=f"Auto-enrolled Student {student} into Program {program} from Opportunity {opportunity.name}",
            title="NBS CRM Auto-Enrollment Success",
        )
    except Exception as e:
        frappe.log_error(
            message=f"Failed to create Program Enrollment for Student {student}, Program {program}: {e}",
            title="NBS CRM Auto-Enrollment PE Error",
        )
