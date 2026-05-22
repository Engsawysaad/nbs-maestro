import frappe
from frappe import _


def on_submit_auto_assign_groups(doc, method):
    """
    CUST-015: Student grouping auto-assignment.

    Triggered on Program Enrollment `on_submit`. Auto-adds the student
    to relevant Student Groups based on:
    - Year/Program group (e.g., "Year 10", "Year 11")
    - Section (if custom section field exists)
    - House (if custom house field exists)

    Student Group naming convention expected:
    - "{program} - {academic_term}" for year groups
    """
    if not doc.student or not doc.program:
        return

    academic_term = doc.academic_term
    if not academic_term:
        frappe.log_error(
            message=f"Program Enrollment {doc.name} has no Academic Term set",
            title="NBS Grouping: Missing Academic Term",
        )
        return

    # 1. Find or create year-group Student Group
    year_group_name = _get_or_create_student_group(doc.program, academic_term)
    if year_group_name:
        _add_student_to_group(year_group_name, doc.student)

    # 2. Section group (if applicable)
    section = doc.get("custom_section") or doc.get("section")
    if section:
        section_group_name = _get_or_create_student_group(
            f"{doc.program} - {section}", academic_term
        )
        if section_group_name:
            _add_student_to_group(section_group_name, doc.student)

    # 3. House group (if applicable)
    house = doc.get("custom_house") or doc.get("house")
    if house:
        house_group_name = _get_or_create_student_group(
            f"House - {house}", academic_term
        )
        if house_group_name:
            _add_student_to_group(house_group_name, doc.student)


def _get_or_create_student_group(group_name, academic_term):
    """Find an existing Student Group by name or create one."""
    existing = frappe.get_value("Student Group", {"student_group_name": group_name})
    if existing:
        return existing

    try:
        group = frappe.get_doc(
            {
                "doctype": "Student Group",
                "student_group_name": group_name,
                "academic_term": academic_term,
                "group_based_on": "Batch",
            }
        )
        group.insert(ignore_permissions=True)
        return group.name
    except Exception as e:
        frappe.log_error(
            message=f"Failed to create Student Group '{group_name}': {e}",
            title="NBS Grouping: Create Group Error",
        )
        return None


def _add_student_to_group(group_name, student_name):
    """Add a student to a Student Group if not already present."""
    existing = frappe.get_all(
        "Student Group Student",
        filters={"parent": group_name, "student": student_name},
        limit=1,
    )
    if existing:
        return

    try:
        group_doc = frappe.get_doc("Student Group", group_name)
        group_doc.append(
            "students",
            {
                "student": student_name,
                "active": 1,
            },
        )
        group_doc.save(ignore_permissions=True)
    except Exception as e:
        frappe.log_error(
            message=f"Failed to add Student {student_name} to Group {group_name}: {e}",
            title="NBS Grouping: Add Student Error",
        )
