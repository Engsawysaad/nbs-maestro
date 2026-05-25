import frappe

def get_context(context):
    context.no_cache = 1
    context.title = "Student Dashboard"
    context.portal_title = "Student Portal"
    context.show_sidebar = True

    student = frappe.call("nbs_school.portal.student_api.get_own_student")
    if student:
        context.student = student
        context.student_data = frappe.call(
            "nbs_school.portal.student_api.get_own_dashboard_data",
            student=student.name,
        )
    else:
        context.student = None
        context.student_data = None

    context.announcements = frappe.call("nbs_school.portal.student_api.get_own_announcements")
