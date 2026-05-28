import frappe
from frappe import _
from frappe.utils import flt


@frappe.whitelist()
def get_linked_students():
    """Get list of students linked to the currently logged-in Guardian."""
    user_email = frappe.session.user

    if user_email == "Guest":
        return []

    guardian_name = frappe.db.get_value("Guardian", {"email_address": user_email})
    if not guardian_name:
        return []

    guardian_doc = frappe.get_doc("Guardian", guardian_name)
    students = []
    for row in guardian_doc.get("students", []):
        students.append({
            "name": row.student,
            "student_name": row.student_name,
            "program": frappe.db.get_value("Program Enrollment", {"student": row.student, "docstatus": 1}, "program"),
            "academic_year": frappe.db.get_value("Program Enrollment", {"student": row.student, "docstatus": 1}, "academic_year"),
        })
    return students


@frappe.whitelist()
def get_student_dashboard_data(student, academic_year=None):
    """Get dashboard data for a specific student."""
    if not academic_year:
        academic_year = (
            frappe.defaults.get_user_default("academic_year")
            or frappe.db.get_single_value("Education Settings", "current_academic_year")
        )

    if not student:
        return {"grades": [], "attendance": {"present": 0, "absent": 0, "late": 0, "percentage": 0}, "fees": [], "timetable": []}

    # ── 1. Grades ──────────────────────────────────────────────
    grades = []
    assessment_results = frappe.get_all(
        "Assessment Result",
        filters={"student": student, "docstatus": 1, "academic_year": academic_year},
        fields=["name", "assessment_plan", "creation"],
        order_by="creation desc",
        limit=20,
    )
    for ar in assessment_results:
        plan_name = frappe.db.get_value("Assessment Plan", ar.assessment_plan, "course")
        details = frappe.get_all(
            "Assessment Result Detail",
            filters={"parent": ar.name},
            fields=["assessment_criteria", "score", "grade"],
        )
        for d in details:
            grades.append({
                "course": plan_name,
                "assessment_criteria": d.assessment_criteria,
                "score": d.score,
                "grade": d.grade,
                "date": ar.creation.strftime("%Y-%m-%d") if ar.creation else "",
            })

    # ── 2. Attendance ──────────────────────────────────────────
    attendance_records = frappe.get_all(
        "Attendance",
        filters={"student": student, "docstatus": 1, "academic_year": academic_year},
        fields=["status"],
    )
    present = sum(1 for r in attendance_records if r.status == "Present")
    absent = sum(1 for r in attendance_records if r.status == "Absent")
    late = sum(1 for r in attendance_records if r.status == "Late")
    total = present + absent + late
    percentage = round((present / total) * 100, 1) if total > 0 else 0

    attendance = {
        "present": present,
        "absent": absent,
        "late": late,
        "percentage": percentage,
    }

    # ── 3. Fees ────────────────────────────────────────────────
    fees = frappe.get_all(
        "Sales Invoice",
        filters={"student": student, "docstatus": 1, "academic_year": academic_year},
        fields=["name", "posting_date", "grand_total", "outstanding_amount"],
        order_by="posting_date desc",
        limit=10,
    )
    fee_list = []
    for f in fees:
        fee_list.append({
            "invoice_no": f.name,
            "posting_date": f.posting_date.strftime("%Y-%m-%d") if f.posting_date else "",
            "grand_total": flt(f.grand_total),
            "outstanding_amount": flt(f.outstanding_amount),
            "status": "Paid" if flt(f.outstanding_amount) <= 0 else "Unpaid",
        })

    # ── 4. Timetable ───────────────────────────────────────────
    timetable = []
    program_enrollments = frappe.get_all(
        "Program Enrollment",
        filters={"student": student, "docstatus": 1, "academic_year": academic_year},
        fields=["name", "program", "academic_term"],
    )
    if program_enrollments:
        pe = program_enrollments[0]
        student_groups = frappe.get_all(
            "Student Group Student",
            filters={"parenttype": "Student Group", "student": student},
            pluck="parent",
        )
        if student_groups:
            courses = frappe.get_all(
                "Student Group",
                filters={"name": ("in", student_groups), "academic_year": academic_year},
                fields=["name", "course"],
            )
            course_names = [c.course for c in courses if c.course]
            if course_names:
                timetable_raw = frappe.db.sql(
                    """
                    SELECT cs.course, cs.instructor, cs.room, cs.day,
                           cs.from_time, cs.to_time, cs.date
                    FROM `tabCourse Schedule` cs
                    WHERE cs.course IN %(courses)s
                      AND (cs.academic_year = %(year)s OR cs.academic_term = %(term)s OR %(year)s IS NULL)
                    ORDER BY
                      FIELD(cs.day, 'Monday','Tuesday','Wednesday','Thursday','Friday','Saturday','Sunday'),
                      cs.from_time
                    LIMIT 20
                    """,
                    {
                        "courses": course_names,
                        "year": academic_year,
                        "term": pe.get("academic_term") or "",
                    },
                    as_dict=True,
                )
                for t in timetable_raw:
                    timetable.append({
                        "course": t.course,
                        "instructor": t.instructor,
                        "room": t.room,
                        "day": t.day,
                        "from_time": str(t.from_time or ""),
                        "to_time": str(t.to_time or ""),
                        "date": t.date.strftime("%Y-%m-%d") if t.date else "",
                    })

    return {
        "grades": grades,
        "attendance": attendance,
        "fees": fee_list,
        "timetable": timetable,
    }


@frappe.whitelist()
def render_progress_report_html(student):
    """Render the NBS School Report Card print format for a student (parent access)."""
    student_doc = frappe.get_doc("Student", student)
    pf = frappe.get_doc("Print Format", "NBS School Report Card")
    html = frappe.render_template(pf.html, {"doc": student_doc})
    return html

@frappe.whitelist()
def get_announcements():
    """Get published school announcements."""
    try:
        announcements = frappe.get_all(
            "NBS Announcement",
            filters={"published": 1},
            fields=["title", "content", "publish_date", "audience"],
            order_by="publish_date desc",
            limit=10,
        )
        for a in announcements:
            if hasattr(a.get("publish_date"), "strftime"):
                a["publish_date"] = a.publish_date.strftime("%Y-%m-%d")
        return announcements
    except Exception:
        return []
