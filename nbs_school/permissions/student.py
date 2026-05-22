import frappe


def student_query_conditions(user):
    """
    CUST-045: Permission query conditions for Student.

    - NBS Teacher: sees only students in their Course Schedules
    - NBS Student Portal: sees only themselves
    - NBS Parent: sees only their own children
    - Senior roles: no restriction
    """
    if not user:
        user = frappe.session.user

    roles = frappe.get_roles(user)

    bypass_roles = {
        "Administrator", "NBS CEO", "NBS Head of School", "NBS School Admin",
        "NBS IT Support", "NBS Board Member", "NBS Finance Manager",
        "NBS Admissions Lead", "NBS Admissions Officer", "NBS HR Manager",
    }
    if bypass_roles & set(roles):
        return ""

    # NBS Teacher: students in their Course Schedules
    if "NBS Teacher" in roles:
        instructor = frappe.db.get_value("Instructor", {"user_id": user}, "name")
        if instructor:
            return (
                "`tabStudent`.name IN ("
                "SELECT DISTINCT student FROM `tabStudent Group Student` "
                "WHERE parent IN ("
                "SELECT student_group FROM `tabCourse Schedule` "
                f"WHERE instructor = {frappe.db.escape(instructor)}"
                "))"
            )
        return "1=0"

    # NBS Student Portal: only themselves
    if "NBS Student Portal" in roles:
        return f"`tabStudent`.student_email_id = {frappe.db.escape(user)}"

    # NBS Parent: their children
    if "NBS Parent" in roles:
        guardian = frappe.db.get_value("Guardian", {"email_address": user}, "name")
        if guardian:
            return (
                "`tabStudent`.name IN ("
                "SELECT student FROM `tabGuardian Student` "
                f"WHERE parent = {frappe.db.escape(guardian)}"
                ")"
            )
        return "1=0"

    return ""


def has_student_permission(doc, ptype, user):
    """
    CUST-046: Document-level permission check for Student.
    """
    if not user:
        user = frappe.session.user

    roles = frappe.get_roles(user)

    bypass_roles = {
        "Administrator", "NBS CEO", "NBS Head of School", "NBS School Admin",
        "NBS IT Support", "NBS Board Member",
    }
    if bypass_roles & set(roles):
        return None

    # Teacher: check if student is in their course schedules
    if "NBS Teacher" in roles:
        instructor = frappe.db.get_value("Instructor", {"user_id": user}, "name")
        if instructor:
            enrolled = frappe.db.exists(
                "Student Group Student",
                {
                    "student": doc.name,
                    "parent": (
                        "in",
                        frappe.get_all(
                            "Course Schedule",
                            {"instructor": instructor},
                            pluck="student_group",
                        ),
                    ),
                },
            )
            if enrolled:
                return None
        return False

    # Student Portal: only themselves
    if "NBS Student Portal" in roles:
        if doc.student_email_id == user:
            return None
        return False

    # Parent: only their children
    if "NBS Parent" in roles:
        guardian = frappe.db.get_value("Guardian", {"email_address": user}, "name")
        if guardian:
            linked = frappe.db.exists(
                "Guardian Student",
                {"parent": guardian, "student": doc.name},
            )
            if linked:
                return None
        return False

    return None
