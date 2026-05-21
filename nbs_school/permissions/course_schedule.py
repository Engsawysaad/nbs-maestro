import frappe
from frappe import _


def course_schedule_query_conditions(user):
    """
    Permission query conditions for Course Schedule.

    Restricts list view to:
    - NBS Teacher: sees only Course Schedules where they are the instructor
    - NBS Student Portal: sees only Course Schedules linked to their Program Enrollment
    - NBS Parent: sees only Course Schedules linked to their children's Program Enrollment
    - All other NBS roles: no additional restriction (full list access as per role permissions)
    """
    if not user:
        user = frappe.session.user

    roles = frappe.get_roles(user)

    # Administrators and certain roles bypass restrictions
    bypass_roles = {"Administrator", "NBS CEO", "NBS Head of School", "NBS School Admin",
                    "NBS IT Support", "NBS Board Member", "NBS Finance Manager",
                    "NBS Admissions Lead", "NBS Admissions Officer"}
    if bypass_roles & set(roles):
        return ""

    # NBS Teacher: only their own course schedules
    if "NBS Teacher" in roles:
        instructor = frappe.db.get_value("Instructor", {"user_id": user}, "name")
        if instructor:
            return f"`tabCourse Schedule`.instructor = {frappe.db.escape(instructor)}"
        return "1=0"

    # NBS Student Portal: schedules from their enrolled programs
    if "NBS Student Portal" in roles:
        student = frappe.db.get_value("Student", {"student_email_id": user}, "name")
        if student:
            return f"`tabCourse Schedule`.student_group IN (SELECT `tabStudent Group`.name FROM `tabStudent Group` WHERE `tabStudent Group`.group_based_on = 'Batch' AND EXISTS (SELECT 1 FROM `tabProgram Enrollment` WHERE `tabProgram Enrollment`.student = {frappe.db.escape(student)} AND `tabProgram Enrollment`.program = `tabCourse Schedule`.program AND `tabProgram Enrollment`.docstatus = 1))"
        return "1=0"

    # NBS Parent: schedules from their children's programs
    if "NBS Parent" in roles:
        guardian = frappe.db.get_value("Guardian", {"email_address": user}, "name")
        if guardian:
            return f"`tabCourse Schedule`.student_group IN (SELECT `tabStudent Group`.name FROM `tabStudent Group` WHERE `tabStudent Group`.group_based_on = 'Batch' AND EXISTS (SELECT 1 FROM `tabProgram Enrollment` WHERE `tabProgram Enrollment`.student IN (SELECT student FROM `tabGuardian Student` WHERE parent = {frappe.db.escape(guardian)}) AND `tabProgram Enrollment`.program = `tabCourse Schedule`.program AND `tabProgram Enrollment`.docstatus = 1))"
        return "1=0"

    return ""


def has_course_schedule_permission(doc, ptype, user):
    """
    Document-level permission check for Course Schedule.

    Can only deny access (return False). Returns None to fall through to standard checks.
    """
    if not user:
        user = frappe.session.user

    roles = frappe.get_roles(user)

    # Bypass for administrators and senior roles
    bypass_roles = {"Administrator", "NBS CEO", "NBS Head of School", "NBS School Admin",
                    "NBS IT Support", "NBS Board Member"}
    if bypass_roles & set(roles):
        return None

    return None


def on_submit_auto_user_permission(doc, method):
    """
    Auto-create User Permission on Course Schedule submit.

    Creates User Permission records so that:
    - The instructor can access the Course Schedule
    - Students enrolled in the linked Student Group can access it
    - Guardians of enrolled students can access it
    """
    if not doc.student_group:
        return

    # Get instructor user
    if doc.instructor:
        instructor_user = frappe.db.get_value("Instructor", doc.instructor, "user_id")
        if instructor_user and instructor_user != "Administrator":
            _add_user_permission("Course Schedule", doc.name, instructor_user)

    # Get students in the group
    students = frappe.get_all("Student Group Student",
        filters={"parent": doc.student_group, "active": 1},
        fields=["student"])

    for s in students:
        student_user = frappe.db.get_value("Student", s.student, "student_email_id")
        if student_user and student_user != "Administrator":
            _add_user_permission("Course Schedule", doc.name, student_user)

        # Also add for guardians
        guardians = frappe.get_all("Guardian Student",
            filters={"student": s.student},
            fields=["parent"])
        for g in guardians:
            guardian_user = frappe.db.get_value("Guardian", g.parent, "email_address")
            if guardian_user and guardian_user != "Administrator":
                _add_user_permission("Course Schedule", doc.name, guardian_user)


def _add_user_permission(dt, docname, user):
    """Add User Permission if it doesn't already exist."""
    existing = frappe.get_all("User Permission",
        filters={
            "allow": dt,
            "for_value": docname,
            "user": user,
            "apply_to_all_doctypes": 1
        },
        limit=1)
    if existing:
        return

    perm = frappe.get_doc({
        "doctype": "User Permission",
        "allow": dt,
        "for_value": docname,
        "user": user,
        "apply_to_all_doctypes": 1
    })
    try:
        perm.insert(ignore_permissions=True)
    except Exception as e:
        frappe.log_error(
            message=f"Failed to create User Permission for {dt} {docname} for user {user}: {e}",
            title="NBS User Permission Error"
        )
