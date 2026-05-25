import frappe
from frappe import _


def get_context(context):
    context.no_cache = 1
    context.title = _("Parent Dashboard")
    context.portal_title = _("Parent Portal")
    context.show_sidebar = True

    # Get linked students for this guardian
    students = frappe.call("nbs_school.portal.parent_api.get_linked_students")
    if students:
        context.students = students
        selected = frappe.request.args.get("student") or students[0].get("name")
        context.selected_student = selected
        context.student_data = frappe.call(
            "nbs_school.portal.parent_api.get_student_dashboard_data",
            student=selected,
        )
    else:
        context.students = []
        context.student_data = None

    context.announcements = frappe.call(
        "nbs_school.portal.parent_api.get_announcements"
    )
