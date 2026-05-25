import frappe
from frappe import _


def execute(filters=None):
    """NBS IGCSE Entry Summary — Script Report.

    Summarises IGCSE exam entry fees by subject/course, showing:
        - Candidate count per subject
        - Entry fee breakdown (total, paid, outstanding)
        - Payment status (Paid / Partial / Unpaid)

    Data pipeline:
        IGCSE Program → Course Enrollment → Student → Sales Invoice (fee status)
    """
    columns = get_columns()
    data = get_data(filters)
    return columns, data


def get_columns():
    """Return report column definitions."""
    return [
        {
            "fieldname": "subject",
            "label": _("Subject / Course"),
            "fieldtype": "Link",
            "options": "Course",
            "width": 220,
        },
        {
            "fieldname": "candidate_count",
            "label": _("Candidate Count"),
            "fieldtype": "Int",
            "width": 140,
        },
        {
            "fieldname": "entry_fee_per_student",
            "label": _("Entry Fee per Student (KWD)"),
            "fieldtype": "Currency",
            "options": "KWD",
            "width": 200,
        },
        {
            "fieldname": "total_fee",
            "label": _("Total Fee (KWD)"),
            "fieldtype": "Currency",
            "options": "KWD",
            "width": 150,
        },
        {
            "fieldname": "paid",
            "label": _("Paid (KWD)"),
            "fieldtype": "Currency",
            "options": "KWD",
            "width": 150,
        },
        {
            "fieldname": "outstanding",
            "label": _("Outstanding (KWD)"),
            "fieldtype": "Currency",
            "options": "KWD",
            "width": 150,
        },
        {
            "fieldname": "payment_status",
            "label": _("Payment Status"),
            "fieldtype": "Data",
            "width": 140,
        },
    ]


def get_conditions(filters):
    """Build dynamic WHERE clause and parameter dict from filters."""
    conditions = []
    params = {"academic_year": filters.get("academic_year")}

    if filters and filters.get("exam_session"):
        conditions.append("ce.exam_session = %(exam_session)s")
        params["exam_session"] = filters["exam_session"]

    return conditions, params


def get_data(filters):
    """Fetch IGCSE course enrollments and aggregate entry fee data."""
    conditions, params = get_conditions(filters)
    where_clause = " AND ".join(conditions) if conditions else "1=1"

    # ── Step 1: Fetch all IGCSE Course Enrollments ──────────────
    try:
        enrollments = frappe.db.sql(
            f"""
            SELECT
                ce.name,
                ce.student,
                ce.course,
                cou.course_name,
                COALESCE(ce.entry_fee, 0) AS entry_fee
            FROM `tabCourse Enrollment` ce
            INNER JOIN `tabProgram` prog
                ON prog.name = ce.program
            INNER JOIN `tabCourse` cou
                ON cou.name = ce.course
            WHERE prog.program_name LIKE '%IGCSE%'
                AND ce.academic_year = %(academic_year)s
                AND {where_clause}
                AND ce.docstatus < 2
            ORDER BY cou.course_name, ce.student
            """,
            params,
            as_dict=True,
        )

        if not enrollments:
            return []

        # ── Step 2: Build student → total entry fee map ──────────
        student_total_entry = {}
        for e in enrollments:
            student_total_entry[e.student] = (
                student_total_entry.get(e.student, 0) + e.entry_fee
            )

        # ── Step 3: Fetch Sales Invoice data for these students ──
        student_payments = frappe.db.sql(
            """
            SELECT
                si.student,
                SUM(si.grand_total) AS total_invoiced,
                SUM(si.outstanding_amount) AS total_outstanding
            FROM `tabSales Invoice` si
            WHERE si.docstatus = 1
                AND si.academic_year = %(academic_year)s
                AND si.student IN %(students)s
            GROUP BY si.student
            """,
            {
                "academic_year": filters.get("academic_year"),
                "students": list(student_total_entry.keys()),
            },
            as_dict=True,
        )

        payment_map = {p.student: p for p in student_payments}

        # ── Step 4: Aggregate by course, allocating payments ─────
        #        proportionally based on each student's entry fee
        #        split across their enrolled IGCSE subjects.
        course_map = {}
        for e in enrollments:
            cd = course_map.setdefault(
                e.course_name,
                {
                    "subject": e.course_name,
                    "candidate_count": 0,
                    "entry_fee_per_student": 0,
                    "total_fee": 0,
                    "paid": 0.0,
                    "outstanding": 0.0,
                    "_students": set(),
                },
            )
            cd["_students"].add(e.student)
            cd["total_fee"] += e.entry_fee

            # Allocate each student's total invoice paid/outstanding
            # to this course in proportion to what this course's
            # entry fee represents of the student's total IGCSE fees.
            if e.student in payment_map:
                p = payment_map[e.student]
                total_entry = student_total_entry[e.student]
                ratio = e.entry_fee / total_entry if total_entry > 0 else 0
                total_paid = (p.total_invoiced or 0) - (p.total_outstanding or 0)
                cd["paid"] += total_paid * ratio
                cd["outstanding"] += (p.total_outstanding or 0) * ratio

        # ── Step 5: Finalise & derive computed fields ────────────
        result = []
        for course_name in sorted(course_map.keys()):
            cd = course_map[course_name]
            cd["candidate_count"] = len(cd["_students"])
            cd["entry_fee_per_student"] = (
                round(cd["total_fee"] / cd["candidate_count"], 3)
                if cd["candidate_count"] > 0
                else 0
            )
            cd["paid"] = round(cd["paid"], 3)
            cd["outstanding"] = round(cd["outstanding"], 3)

            # Derive payment status
            if cd["paid"] >= cd["total_fee"] and cd["total_fee"] > 0:
                cd["payment_status"] = _("Paid")
            elif cd["paid"] > 0:
                cd["payment_status"] = _("Partial")
            else:
                cd["payment_status"] = _("Unpaid")

            del cd["_students"]
            result.append(cd)

        return result

    except Exception as e:
        frappe.log_error(
            message=f"Error in NBS IGCSE Entry Summary Report: {str(e)}",
            title="NBS IGCSE Entry Summary Report Error",
        )
        return []
