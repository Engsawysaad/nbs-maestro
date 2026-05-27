import frappe
from nbs_school.portal.student_api import get_own_student, get_own_dashboard_data, get_own_announcements


def get_context(context):
    context.no_cache = 1
    context.title = "Student Dashboard"
    context.portal_title = "Student Portal"
    context.show_sidebar = True
    context.is_guest = frappe.session.user == "Guest"

    student = get_own_student()
    if student:
        context.student = student
        context.student_data = get_own_dashboard_data(student=student.name)
    else:
        context.student = None
        context.student_data = None

    context.announcements = get_own_announcements()
