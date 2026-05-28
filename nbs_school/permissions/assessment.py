import frappe


def assessment_query_conditions(user):
    """
    CUST-045: Permission query conditions for Assessment Result.

    - NBS Teacher: sees only results for students in their Course Schedules
    - NBS Student Portal: sees only their own results
    - NBS Parent: sees only their children's results
    - Senior roles: no restriction
    """
    if not user:
        user = frappe.session.user

    roles = frappe.get_roles(user)

    bypass_roles = {
        "Administrator", "System Manager", "NBS CEO", "NBS Head of School", "NBS School Admin",
        "NBS IT Support", "NBS Board Member", "NBS Finance Manager",
        "NBS Admissions Lead",
    }
    if bypass_roles & set(roles):
        return ""

    if "NBS Teacher" in roles:
        instructor = frappe.db.get_value("Instructor", {"user_id": user}, "name")
        if instructor:
            return (
                "`tabAssessment Result`.student IN ("
                "SELECT DISTINCT student FROM `tabStudent Group Student` "
                "WHERE parent IN ("
                "SELECT student_group FROM `tabCourse Schedule` "
                f"WHERE instructor = {frappe.db.escape(instructor)}"
                "))"
            )
        return "1=0"

    if "NBS Student Portal" in roles:
        student = frappe.db.get_value("Student", {"student_email_id": user}, "name")
        if student:
            return f"`tabAssessment Result`.student = {frappe.db.escape(student)}"
        return "1=0"

    if "NBS Parent" in roles:
        guardian = frappe.db.get_value("Guardian", {"email_address": user}, "name")
        if guardian:
            return (
                "`tabAssessment Result`.student IN ("
                "SELECT student FROM `tabGuardian Student` "
                f"WHERE parent = {frappe.db.escape(guardian)}"
                ")"
            )
        return "1=0"

    return ""


def has_assessment_permission(doc, ptype, user):
    """
    CUST-046: Document-level permission check for Assessment Result.
    """
    if not user:
        user = frappe.session.user

    roles = frappe.get_roles(user)

    bypass_roles = {
        "Administrator", "System Manager", "NBS CEO", "NBS Head of School", "NBS School Admin",
        "NBS IT Support", "NBS Board Member",
    }
    if bypass_roles & set(roles):
        return None

    if "NBS Teacher" in roles:
        instructor = frappe.db.get_value("Instructor", {"user_id": user}, "name")
        if instructor:
            enrolled = frappe.db.exists(
                "Student Group Student",
                {
                    "student": doc.student,
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

    if "NBS Student Portal" in roles:
        student = frappe.db.get_value("Student", {"student_email_id": user}, "name")
        if student and doc.student == student:
            return None
        return False

    if "NBS Parent" in roles:
        guardian = frappe.db.get_value("Guardian", {"email_address": user}, "name")
        if guardian:
            linked = frappe.db.exists(
                "Guardian Student",
                {"parent": guardian, "student": doc.student},
            )
            if linked:
                return None
        return False

    return None
