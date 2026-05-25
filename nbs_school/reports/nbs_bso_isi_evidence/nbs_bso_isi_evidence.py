import frappe
from frappe import _

# ── Evidence type → inspection criterion mapping ─────────────
EVIDENCE_CRITERION_MAP = {
    "Assessment Plan": ["Assessment", "Curriculum"],
    "Course Schedule": ["Quality of Teaching", "Curriculum"],
    "Attendance Record": ["Safeguarding", "Personal Development"],
    "Staff Record": ["Leadership and Management", "Safeguarding"],
    "Student Record": ["Outcomes for Students", "Personal Development"],
}

# ── Module labels per DocType ────────────────────────────────
DOCTYPE_MODULE = {
    "Assessment Plan": _("Student Management"),
    "Course Schedule": _("Student Management"),
    "Attendance": _("Student Management"),
    "Employee": _("Human Resources"),
    "Student": _("Student Management"),
}


def execute(filters=None):
    """NBS BSO/ISI Evidence Report — Script Report.

    Compiles evidence items from across the school management system
    mapped to BSO/ISI inspection criteria for a given Academic Year.
    """
    columns = get_columns()
    data = get_data(filters)
    return columns, data


def get_columns():
    """Return report column definitions."""
    return [
        {
            "fieldname": "inspection_criterion",
            "label": _("Inspection Criterion"),
            "fieldtype": "Data",
            "width": 220,
        },
        {
            "fieldname": "evidence_type",
            "label": _("Evidence Type"),
            "fieldtype": "Data",
            "width": 160,
        },
        {
            "fieldname": "reference_document",
            "label": _("Reference Document"),
            "fieldtype": "Dynamic Link",
            "options": "reference_doctype",
            "width": 220,
        },
        {
            "fieldname": "reference_doctype",
            "label": _("Reference DocType"),
            "fieldtype": "Data",
            "width": 0,
        },
        {
            "fieldname": "source_module",
            "label": _("Source Module"),
            "fieldtype": "Data",
            "width": 160,
        },
        {
            "fieldname": "date",
            "label": _("Date"),
            "fieldtype": "Date",
            "width": 110,
        },
        {
            "fieldname": "link",
            "label": _("Link"),
            "fieldtype": "HTML",
            "width": 80,
        },
    ]


# ═══════════════════════════════════════════════════════════════
#  Data compilation
# ═══════════════════════════════════════════════════════════════

def get_data(filters):
    """Collect and compile evidence rows from across all school modules."""
    academic_year = filters.get("academic_year") if filters else None
    criterion_filter = filters.get("inspection_criterion") if filters else None

    rows = []
    rows.extend(_assessment_plan_evidence(academic_year))
    rows.extend(_course_schedule_evidence(academic_year))
    rows.extend(_attendance_evidence(academic_year))
    rows.extend(_employee_evidence(academic_year))
    rows.extend(_student_evidence(academic_year))

    # Apply optional inspection_criterion filter
    if criterion_filter:
        rows = [r for r in rows if r.get("inspection_criterion") == criterion_filter]

    # Sort by inspection criterion then date (descending)
    rows.sort(key=lambda r: (r.get("inspection_criterion") or "", r.get("date") or ""), reverse=False)

    return rows


def _make_link_html(doctype, name):
    """Return an HTML anchor linking to the document in Desk."""
    if not name:
        return ""
    encoded = name.replace("'", "\\'")
    return f'<a href="/app/{doctype.lower().replace(" ", "-")}/{encoded}" target="_blank">Open</a>'


def _build_row(inspection_criterion, evidence_type, reference_document,
               reference_doctype, date):
    """Construct a single evidence row dict."""
    return {
        "inspection_criterion": inspection_criterion,
        "evidence_type": evidence_type,
        "reference_document": reference_document,
        "reference_doctype": reference_doctype,
        "source_module": DOCTYPE_MODULE.get(reference_doctype, ""),
        "date": date,
        "link": _make_link_html(reference_doctype, reference_document),
    }


# ── 1. Assessment Plan ───────────────────────────────────────

def _assessment_plan_evidence(academic_year):
    """Evidence from Assessment Plans (assessment criteria, schedules)."""
    filters = {"docstatus": 1}
    if academic_year:
        filters["academic_year"] = academic_year

    plans = frappe.get_all(
        "Assessment Plan",
        filters=filters,
        fields=["name", "assessment_criteria", "schedule_date", "course"],
        order_by="schedule_date desc",
    )

    rows = []
    for ap in plans:
        for criterion in EVIDENCE_CRITERION_MAP["Assessment Plan"]:
            rows.append(_build_row(
                inspection_criterion=criterion,
                evidence_type=_("Assessment Plan"),
                reference_document=ap.name,
                reference_doctype="Assessment Plan",
                date=ap.schedule_date,
            ))
    return rows


# ── 2. Course Schedule ───────────────────────────────────────

def _course_schedule_evidence(academic_year):
    """Evidence from Course Schedules (teaching sessions)."""
    filters = {"docstatus": 1}
    if academic_year:
        filters["academic_year"] = academic_year

    schedules = frappe.get_all(
        "Course Schedule",
        filters=filters,
        fields=["name", "schedule_date", "course", "instructor"],
        order_by="schedule_date desc",
    )

    rows = []
    for cs in schedules:
        for criterion in EVIDENCE_CRITERION_MAP["Course Schedule"]:
            rows.append(_build_row(
                inspection_criterion=criterion,
                evidence_type=_("Course Schedule"),
                reference_document=cs.name,
                reference_doctype="Course Schedule",
                date=cs.schedule_date,
            ))
    return rows


# ── 3. Attendance ────────────────────────────────────────────

def _attendance_evidence(academic_year):
    """Evidence from Attendance records (student presence, safeguarding)."""
    filters = {"docstatus": 1, "status": "Present"}
    if academic_year:
        filters["academic_year"] = academic_year

    records = frappe.get_all(
        "Attendance",
        filters=filters,
        fields=["name", "student", "date", "status", "course_schedule"],
        order_by="date desc",
        limit_page_length=500,
    )

    rows = []
    for att in records:
        for criterion in EVIDENCE_CRITERION_MAP["Attendance Record"]:
            rows.append(_build_row(
                inspection_criterion=criterion,
                evidence_type=_("Attendance Record"),
                reference_document=att.name,
                reference_doctype="Attendance",
                date=att.date,
            ))
    return rows


# ── 4. Employee ──────────────────────────────────────────────

def _employee_evidence(academic_year):
    """Evidence from Employee records (staff qualifications, leadership)."""
    filters = {"status": "Active"}
    employees = frappe.get_all(
        "Employee",
        filters=filters,
        fields=["name", "employee_name", "date_of_joining", "department"],
        order_by="date_of_joining desc",
    )

    rows = []
    for emp in employees:
        # Use date_of_joining as the evidence date; attach to academic year if provided
        if academic_year:
            # Only include if date_of_joining falls within the academic year (approximate)
            ay = frappe.db.get_value("Academic Year", academic_year, ["year_start_date", "year_end_date"], as_dict=True)
            if ay:
                if ay.year_start_date and ay.year_end_date:
                    if not (ay.year_start_date <= (emp.date_of_joining or "2000-01-01") <= ay.year_end_date):
                        continue
        for criterion in EVIDENCE_CRITERION_MAP["Staff Record"]:
            rows.append(_build_row(
                inspection_criterion=criterion,
                evidence_type=_("Staff Record"),
                reference_document=emp.name,
                reference_doctype="Employee",
                date=emp.date_of_joining,
            ))
    return rows


# ── 5. Student ───────────────────────────────────────────────

def _student_evidence(academic_year):
    """Evidence from Student records (enrolment, outcomes, progress)."""
    filters = {"enabled": 1}
    if academic_year:
        filters["academic_year"] = academic_year

    students = frappe.get_all(
        "Student",
        filters=filters,
        fields=["name", "student_name", "date_of_birth"],
        order_by="creation desc",
    )

    rows = []
    for stu in students:
        for criterion in EVIDENCE_CRITERION_MAP["Student Record"]:
            rows.append(_build_row(
                inspection_criterion=criterion,
                evidence_type=_("Student Record"),
                reference_document=stu.name,
                reference_doctype="Student",
                date=None,
            ))
    return rows
