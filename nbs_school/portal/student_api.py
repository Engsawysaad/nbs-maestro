import frappe
from frappe import _
from frappe.utils import fmt_money

@frappe.whitelist()
def get_own_student():
    """Get the Student record linked to the logged-in user."""
    user_email = frappe.session.user
    if user_email == "Guest":
        return None

    student = frappe.db.get_value(
        "Student",
        {"student_email_id": user_email},
        ["name", "student_name", "date_of_birth", "student_email_id", "student_mobile_number"],
        as_dict=True,
    )
    if not student:
        return None

    # Get current enrollment
    enrollment = frappe.db.get_value(
        "Program Enrollment",
        {"student": student.name, "docstatus": 1},
        ["name", "program", "academic_year"],
        as_dict=True,
        order_by="creation desc",
    )
    if enrollment:
        student["program_enrollment"] = enrollment.name
        student["program"] = enrollment.program
        student["academic_year"] = enrollment.academic_year

    return student


@frappe.whitelist()
def get_own_dashboard_data(student, academic_year=None):
    """Fetch dashboard data for the given student."""
    if not academic_year:
        academic_year = frappe.defaults.get_user_default("academic_year") or frappe.db.get_single_value(
            "Education Settings", "current_academic_year"
        )

    return {
        "grades": _get_grades(student, academic_year),
        "attendance": _get_attendance(student, academic_year),
        "fees": _get_fees(student, academic_year),
        "timetable": _get_timetable(student, academic_year),
        "profile": _get_profile(student),
    }


@frappe.whitelist()
def render_progress_report_html(student):
    """Render the NBS School Report Card print format for a student.

    Bypasses `print_format.get_html()` which routes to weasyprint (broken for Jinja formats
    that lack format_data layout JSON). Instead renders the Jinja template HTML directly.

    Usage in a Web Page template:
        {{ frappe.call("nbs_school.portal.student_api.render_progress_report_html", {"student": student_name}) }}
    """
    student_doc = frappe.get_doc("Student", student)
    pf = frappe.get_doc("Print Format", "NBS School Report Card")
    pf.doc_type = "Student"
    html = frappe.render_template(pf.html, {"doc": student_doc})
    return html

@frappe.whitelist()
def get_own_announcements():
    """Get published announcements visible to Students."""
    try:
        return frappe.get_all(
            "NBS Announcement",
            filters={"published": 1},
            fields=["title", "content", "publish_date", "priority", "route"],
            order_by="publish_date desc",
            limit=10,
        )
    except Exception:
        return []


def _get_grades(student, academic_year):
    """Fetch assessment results for the student."""
    try:
        results = frappe.get_all(
            "Assessment Result",
            filters={"student": student, "docstatus": 1, "academic_year": academic_year},
            fields=["name", "assessment_plan", "grade", "total_score", "creation_date"],
            order_by="creation_date desc",
            limit=10,
        )
        grades = []
        for r in results:
            plan = frappe.db.get_value("Assessment Plan", r.assessment_plan, "course")
            grades.append({
                "course": plan or "",
                "assessment_criteria": "",
                "score": r.total_score,
                "grade": r.grade,
                "date": r.creation_date,
            })
        return grades
    except Exception as e:
        frappe.log_error(f"Student grades fetch error: {e}", "NBS Student Portal")
        return []


def _get_attendance(student, academic_year):
    """Fetch attendance summary for the student."""
    try:
        records = frappe.db.sql("""
            SELECT
                SUM(CASE WHEN status = 'Present' THEN 1 ELSE 0 END) AS present,
                SUM(CASE WHEN status = 'Absent' THEN 1 ELSE 0 END) AS absent,
                SUM(CASE WHEN status = 'Late' THEN 1 ELSE 0 END) AS late,
                COUNT(*) AS total
            FROM `tabAttendance`
            WHERE student = %(student)s
                AND docstatus = 1
                AND academic_year = %(academic_year)s
        """, {"student": student, "academic_year": academic_year}, as_dict=True)

        rec = records[0] if records else {}
        total = (rec.get("present", 0) or 0) + (rec.get("absent", 0) or 0) + (rec.get("late", 0) or 0)
        return {
            "present": rec.get("present", 0) or 0,
            "absent": rec.get("absent", 0) or 0,
            "late": rec.get("late", 0) or 0,
            "percentage": round((rec.get("present", 0) or 0) / total * 100, 1) if total > 0 else 0,
        }
    except Exception as e:
        frappe.log_error(f"Student attendance fetch error: {e}", "NBS Student Portal")
        return {"present": 0, "absent": 0, "late": 0, "percentage": 0}


def _get_fees(student, academic_year):
    """Fetch fee records for the student."""
    try:
        invoices = frappe.get_all(
            "Sales Invoice",
            filters={"student": student, "docstatus": 1, "academic_year": academic_year},
            fields=["name", "posting_date", "grand_total", "outstanding_amount"],
            order_by="posting_date desc",
            limit=10,
        )
        return [
            {
                "invoice_no": inv.name,
                "posting_date": str(inv.posting_date),
                "grand_total": inv.grand_total,
                "outstanding_amount": inv.outstanding_amount,
                "status": _("Paid") if inv.outstanding_amount <= 0 else _("Unpaid"),
            }
            for inv in invoices
        ]
    except Exception as e:
        frappe.log_error(f"Student fees fetch error: {e}", "NBS Student Portal")
        return []


def _get_timetable(student, academic_year):
    """Fetch timetable for the student's groups."""
    try:
        # Get student's groups
        groups = frappe.get_all(
            "Student Group Student",
            filters={"student": student},
            pluck="parent",
        )
        if not groups:
            return []

        timetable = frappe.db.sql("""
            SELECT
                cs.name,
                cs.course,
                cs.instructor,
                cs.room,
                cs.schedule_date AS date,
                cs.from_time,
                cs.to_time
            FROM `tabCourse Schedule` cs
            WHERE cs.student_group IN %(groups)s
                AND cs.academic_year = %(academic_year)s
                AND cs.docstatus < 2
            ORDER BY cs.schedule_date, cs.from_time
            LIMIT 20
        """, {"groups": groups, "academic_year": academic_year}, as_dict=True)

        return [
            {
                "course": t.course,
                "instructor": t.instructor or "",
                "room": t.room or "",
                "day": "",
                "from_time": str(t.from_time or ""),
                "to_time": str(t.to_time or ""),
                "date": str(t.date or ""),
            }
            for t in timetable
        ]
    except Exception as e:
        frappe.log_error(f"Student timetable fetch error: {e}", "NBS Student Portal")
        return []


def _get_profile(student):
    """Fetch student profile details."""
    try:
        data = frappe.db.get_value(
            "Student", student,
            ["student_name", "date_of_birth", "student_email_id", "student_mobile_number"],
            as_dict=True,
        )
        return data or {"student_name": "", "date_of_birth": "", "student_email_id": "", "student_mobile_number": ""}
    except Exception:
        return {"student_name": "", "date_of_birth": "", "student_email_id": "", "student_mobile_number": ""}
