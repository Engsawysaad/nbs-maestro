import frappe


def fee_query_conditions(user):
    """
    CUST-045: Permission query conditions for Fee-related documents.

    Dispatches to the correct per-doctype function based on the
    currently queried DocType (available via frappe.local.form_dict.doctype).
    """
    doctype = frappe.local.form_dict.get("doctype") if hasattr(frappe.local, "form_dict") else None
    if doctype == "Sales Invoice":
        return _fee_query_conditions_sales_invoice(user)
    return _fee_query_conditions_fee_schedule(user)


def _fee_query_conditions_fee_schedule(user):
    """
    Permission query conditions for Fee Schedule.
    Table name: `tabFee Schedule`
    """
    return _build_fee_query("`tabFee Schedule`", user)


def _fee_query_conditions_sales_invoice(user):
    """
    Permission query conditions for Sales Invoice (fee-related).
    Table name: `tabSales Invoice`
    """
    return _build_fee_query("`tabSales Invoice`", user)


def _build_fee_query(table_name, user):
    """
    Shared permission query condition builder for fee-related DocTypes.

    - NBS Teacher: no fee access (handled by role permissions)
    - NBS Student Portal: sees only their own fee records
    - NBS Parent: sees only their children's fee records
    - Finance/admin roles: no restriction
    """
    if not user:
        user = frappe.session.user

    roles = frappe.get_roles(user)

    bypass_roles = {
        "Administrator", "NBS CEO", "NBS Head of School", "NBS School Admin",
        "NBS IT Support", "NBS Board Member", "NBS Finance Manager",
        "NBS Admissions Lead", "NBS Admissions Officer",
    }
    if bypass_roles & set(roles):
        return ""

    # Teachers have no fee access by role permissions, but if they somehow
    # have read access, restrict to empty
    if "NBS Teacher" in roles:
        return "1=0"

    if "NBS Student Portal" in roles:
        student = frappe.db.get_value("Student", {"student_email_id": user}, "name")
        if student:
            return f"{table_name}.student = {frappe.db.escape(student)}"
        return "1=0"

    if "NBS Parent" in roles:
        guardian = frappe.db.get_value("Guardian", {"email_address": user}, "name")
        if guardian:
            return (
                f"{table_name}.student IN ("
                "SELECT student FROM `tabGuardian Student` "
                f"WHERE parent = {frappe.db.escape(guardian)}"
                ")"
            )
        return "1=0"

    return ""


def has_fee_permission(doc, ptype, user):
    """
    CUST-046: Document-level permission check for Fee documents.
    """
    if not user:
        user = frappe.session.user

    roles = frappe.get_roles(user)

    bypass_roles = {
        "Administrator", "NBS CEO", "NBS Head of School", "NBS School Admin",
        "NBS IT Support", "NBS Board Member", "NBS Finance Manager",
    }
    if bypass_roles & set(roles):
        return None

    if "NBS Student Portal" in roles:
        student = frappe.db.get_value("Student", {"student_email_id": user}, "name")
        if student and getattr(doc, "student", None) == student:
            return None
        return False

    if "NBS Parent" in roles:
        guardian = frappe.db.get_value("Guardian", {"email_address": user}, "name")
        if guardian and getattr(doc, "student", None):
            linked = frappe.db.exists(
                "Guardian Student",
                {"parent": guardian, "student": doc.student},
            )
            if linked:
                return None
        return False

    return None
