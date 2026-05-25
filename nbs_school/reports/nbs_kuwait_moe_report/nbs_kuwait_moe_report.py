import frappe
from frappe import _


def execute(filters=None):
    """NBS Kuwait Ministry of Education (MoE) Annual Statistical Report.

    Three-section hierarchical report:
        1. Student Statistics — by program, nationality (Student Category), gender
        2. Staff Statistics   — total, by department, qualified teachers
        3. Facilities         — classrooms, labs, library, sports
    """
    columns = get_columns()
    data = get_data(filters)
    return columns, data


# ═══════════════════════════════════════════════════════════════
#  Column definitions
# ═══════════════════════════════════════════════════════════════

def get_columns():
    """Return report column definitions.

    The ``indent`` column (hidden, width 0) drives the tree-like
    hierarchy shown in the ``label`` column:
        - indent = 0 → section / sub-section header (bold via JS formatter)
        - indent = 1 → data row with a numeric ``value``
    """
    return [
        {
            "fieldname": "indent",
            "label": _(""),
            "fieldtype": "Int",
            "width": 0,
        },
        {
            "fieldname": "label",
            "label": _("Item"),
            "fieldtype": "Data",
            "width": 420,
        },
        {
            "fieldname": "value",
            "label": _("Count"),
            "fieldtype": "Int",
            "width": 120,
        },
    ]


# ═══════════════════════════════════════════════════════════════
#  Main data compiler
# ═══════════════════════════════════════════════════════════════

def get_data(filters):
    """Compile rows for all three report sections."""
    academic_year = filters.get("academic_year") if filters else None
    if not academic_year:
        return []

    rows = []

    # ──────────────────────────────────────────────────────────
    #  Section 1 — Student Statistics
    # ──────────────────────────────────────────────────────────
    rows.append({"indent": 0, "label": _("1. Student Statistics"), "value": None})

    # 1a. Enrolled students by Program
    rows.append({"indent": 0, "label": _("Enrolled Students by Program"), "value": None})
    for row in get_students_by_program(academic_year):
        rows.append({
            "indent": 1,
            "label": row.get("program") or _("(not set)"),
            "value": row.get("count", 0),
        })

    # 1b. Students by Nationality (Student Category)
    rows.append({"indent": 0, "label": _("Students by Nationality (Student Category)"), "value": None})
    for row in get_students_by_category(academic_year):
        rows.append({
            "indent": 1,
            "label": row.get("student_category") or _("(not set)"),
            "value": row.get("count", 0),
        })

    # 1c. Students by Gender
    rows.append({"indent": 0, "label": _("Students by Gender"), "value": None})
    for row in get_students_by_gender(academic_year):
        rows.append({
            "indent": 1,
            "label": row.get("gender") or _("(not set)"),
            "value": row.get("count", 0),
        })

    # ──────────────────────────────────────────────────────────
    #  Section 2 — Staff Statistics
    # ──────────────────────────────────────────────────────────
    rows.append({"indent": 0, "label": _("2. Staff Statistics"), "value": None})

    # 2a. Total staff
    rows.append({
        "indent": 1,
        "label": _("Total Staff"),
        "value": get_total_staff(),
    })

    # 2b. Staff by Department
    rows.append({"indent": 0, "label": _("Staff by Department"), "value": None})
    for row in get_staff_by_department():
        rows.append({
            "indent": 1,
            "label": row.get("department") or _("(not set)"),
            "value": row.get("count", 0),
        })

    # 2c. Qualified teachers
    rows.append({
        "indent": 1,
        "label": _("Qualified Teachers"),
        "value": get_qualified_teachers(),
    })

    # ──────────────────────────────────────────────────────────
    #  Section 3 — Facilities
    # ──────────────────────────────────────────────────────────
    rows.append({"indent": 0, "label": _("3. Facilities"), "value": None})

    rows.append({
        "indent": 1,
        "label": _("Classrooms"),
        "value": get_classrooms(academic_year),
    })
    rows.append({
        "indent": 1,
        "label": _("Laboratories"),
        "value": get_labs(academic_year),
    })
    rows.append({
        "indent": 1,
        "label": _("Library"),
        "value": get_library_facilities(academic_year),
    })
    rows.append({
        "indent": 1,
        "label": _("Sports Facilities"),
        "value": get_sports_facilities(academic_year),
    })

    return rows


# ═══════════════════════════════════════════════════════════════
#  Data helpers — Section 1: Student Statistics
# ═══════════════════════════════════════════════════════════════

def get_students_by_program(academic_year):
    """Count enrolled students grouped by Program."""
    return frappe.db.sql(
        """
        SELECT
            pe.program,
            COUNT(DISTINCT pe.student) AS count
        FROM `tabProgram Enrollment` pe
        INNER JOIN `tabStudent` s
            ON s.name = pe.student
        WHERE pe.docstatus = 1
            AND pe.academic_year = %(academic_year)s
            AND s.enabled = 1
        GROUP BY pe.program
        ORDER BY pe.program
        """,
        {"academic_year": academic_year},
        as_dict=True,
    )


def get_students_by_category(academic_year):
    """Count enrolled students grouped by Student Category (nationality proxy)."""
    return frappe.db.sql(
        """
        SELECT
            s.student_category,
            COUNT(DISTINCT s.name) AS count
        FROM `tabStudent` s
        INNER JOIN `tabProgram Enrollment` pe
            ON pe.student = s.name
        WHERE pe.docstatus = 1
            AND pe.academic_year = %(academic_year)s
            AND s.enabled = 1
        GROUP BY s.student_category
        ORDER BY s.student_category
        """,
        {"academic_year": academic_year},
        as_dict=True,
    )


def get_students_by_gender(academic_year):
    """Count enrolled students grouped by Gender."""
    return frappe.db.sql(
        """
        SELECT
            s.gender,
            COUNT(DISTINCT s.name) AS count
        FROM `tabStudent` s
        INNER JOIN `tabProgram Enrollment` pe
            ON pe.student = s.name
        WHERE pe.docstatus = 1
            AND pe.academic_year = %(academic_year)s
            AND s.enabled = 1
        GROUP BY s.gender
        ORDER BY s.gender
        """,
        {"academic_year": academic_year},
        as_dict=True,
    )


# ═══════════════════════════════════════════════════════════════
#  Data helpers — Section 2: Staff Statistics
# ═══════════════════════════════════════════════════════════════

def get_total_staff():
    """Return the number of active employees."""
    return frappe.db.count("Employee", {"status": "Active"})


def get_staff_by_department():
    """Count active employees grouped by Department."""
    return frappe.db.sql(
        """
        SELECT
            department,
            COUNT(name) AS count
        FROM `tabEmployee`
        WHERE status = 'Active'
        GROUP BY department
        ORDER BY department
        """,
        as_dict=True,
    )


def get_qualified_teachers():
    """Return the number of active employees flagged as qualified teachers.

    Uses the ``custom_qualified`` field if it exists on the site's
    Employee DocType; otherwise falls back to counting employees
    whose department name contains 'Academic' or 'Teaching'.
    """
    try:
        return frappe.db.count("Employee", {"status": "Active", "custom_qualified": 1})
    except Exception:
        pass

    # Fallback — heuristic based on department name
    try:
        result = frappe.db.sql(
            """
            SELECT COUNT(name) AS count
            FROM `tabEmployee`
            WHERE status = 'Active'
              AND (
                  LOWER(department) LIKE '%academic%'
                  OR LOWER(department) LIKE '%teaching%'
                  OR LOWER(department) LIKE '%faculty%'
              )
            """,
            as_dict=True,
        )
        return result[0]["count"] if result else 0
    except Exception:
        return 0


# ═══════════════════════════════════════════════════════════════
#  Data helpers — Section 3: Facilities
# ═══════════════════════════════════════════════════════════════

def get_classrooms(academic_year):
    """Count distinct classroom rooms from Course Schedule (non-lab)."""
    result = frappe.db.sql(
        """
        SELECT COUNT(DISTINCT room) AS count
        FROM `tabCourse Schedule`
        WHERE docstatus = 1
            AND academic_year = %(academic_year)s
            AND room IS NOT NULL
            AND room != ''
            AND UPPER(room) NOT LIKE '%LAB%'
        """,
        {"academic_year": academic_year},
        as_dict=True,
    )
    return result[0]["count"] if result else 0


def get_labs(academic_year):
    """Count distinct laboratory rooms from Course Schedule."""
    result = frappe.db.sql(
        """
        SELECT COUNT(DISTINCT room) AS count
        FROM `tabCourse Schedule`
        WHERE docstatus = 1
            AND academic_year = %(academic_year)s
            AND room IS NOT NULL
            AND room != ''
            AND UPPER(room) LIKE '%LAB%'
        """,
        {"academic_year": academic_year},
        as_dict=True,
    )
    return result[0]["count"] if result else 0


def get_library_facilities(academic_year):
    """Count distinct library rooms from Course Schedule."""
    result = frappe.db.sql(
        """
        SELECT COUNT(DISTINCT room) AS count
        FROM `tabCourse Schedule`
        WHERE docstatus = 1
            AND academic_year = %(academic_year)s
            AND room IS NOT NULL
            AND room != ''
            AND UPPER(room) LIKE '%LIBRARY%'
        """,
        {"academic_year": academic_year},
        as_dict=True,
    )
    return result[0]["count"] if result else 0


def get_sports_facilities(academic_year):
    """Count distinct sports / gym / playground rooms from Course Schedule."""
    result = frappe.db.sql(
        """
        SELECT COUNT(DISTINCT room) AS count
        FROM `tabCourse Schedule`
        WHERE docstatus = 1
            AND academic_year = %(academic_year)s
            AND room IS NOT NULL
            AND room != ''
            AND (
                UPPER(room) LIKE '%SPORT%'
                OR UPPER(room) LIKE '%GYM%'
                OR UPPER(room) LIKE '%PLAYGROUND%'
                OR UPPER(room) LIKE '%FIELD%'
                OR UPPER(room) LIKE '%POOL%'
                OR UPPER(room) LIKE '%COURT%'
            )
        """,
        {"academic_year": academic_year},
        as_dict=True,
    )
    return result[0]["count"] if result else 0
