import frappe
from frappe import _


def execute(filters=None):
    """NBS Sibling Discount — Script Report.

    Groups fee invoice data by Guardian (family) to show sibling
    discount applied across multiple enrolled students within an
    academic term.
    """
    if not filters or not filters.get("academic_term"):
        frappe.throw(_("Academic Term is mandatory"))
        return [], []

    columns = get_columns()
    data = get_data(filters)
    chart = get_chart(data)
    report_summary = get_summary(data)
    return columns, data, None, chart, report_summary


def get_columns():
    """Return report column definitions."""
    return [
        {
            "fieldname": "guardian_name",
            "label": _("Family / Guardian Name"),
            "fieldtype": "Data",
            "width": 250,
        },
        {
            "fieldname": "students_enrolled",
            "label": _("Students Enrolled"),
            "fieldtype": "Int",
            "width": 150,
        },
        {
            "fieldname": "student_names",
            "label": _("Student Names"),
            "fieldtype": "Data",
            "width": 300,
        },
        {
            "fieldname": "programs",
            "label": _("Programs"),
            "fieldtype": "Data",
            "width": 200,
        },
        {
            "fieldname": "total_fee_before_discount",
            "label": _("Total Fee Before Discount (KWD)"),
            "fieldtype": "Currency",
            "options": "KWD",
            "width": 180,
        },
        {
            "fieldname": "total_discount",
            "label": _("Total Discount (KWD)"),
            "fieldtype": "Currency",
            "options": "KWD",
            "width": 160,
        },
        {
            "fieldname": "discount_percent",
            "label": _("Discount %"),
            "fieldtype": "Percent",
            "width": 120,
        },
    ]


def get_data(filters):
    """Fetch and aggregate fee data grouped by Guardian / family."""
    academic_term = filters.get("academic_term")

    try:
        data = frappe.db.sql(
            """
            SELECT
                g.name AS guardian_id,
                COALESCE(g.guardian_name, g.name) AS guardian_name,
                COUNT(DISTINCT s.name) AS students_enrolled,
                GROUP_CONCAT(
                    DISTINCT s.student_name
                    ORDER BY s.student_name
                    SEPARATOR ', '
                ) AS student_names,
                GROUP_CONCAT(
                    DISTINCT pe.program
                    ORDER BY pe.program
                    SEPARATOR ', '
                ) AS programs,
                COALESCE(SUM(si.base_total), 0) AS total_fee_before_discount,
                COALESCE(SUM(si.discount_amount), 0) AS total_discount,
                CASE
                    WHEN COALESCE(SUM(si.base_total), 0) > 0
                    THEN ROUND(
                        COALESCE(SUM(si.discount_amount), 0)
                        / COALESCE(SUM(si.base_total), 0) * 100,
                        2
                    )
                    ELSE 0
                END AS discount_percent
            FROM `tabGuardian` g
            INNER JOIN `tabGuardian Student` gs
                ON gs.parent = g.name
                AND gs.parenttype = 'Guardian'
            INNER JOIN `tabStudent` s
                ON s.name = gs.student
            INNER JOIN `tabProgram Enrollment` pe
                ON pe.student = s.name
                AND pe.academic_term = %(academic_term)s
                AND pe.docstatus = 1
            LEFT JOIN `tabSales Invoice` si
                ON si.student = s.name
                AND si.academic_term = %(academic_term)s
                AND si.docstatus = 1
                AND si.naming_series LIKE 'NBS-INV-%%'
            WHERE gs.student IS NOT NULL
                AND s.enabled = 1
            GROUP BY g.name, g.guardian_name
            ORDER BY g.guardian_name
            """,
            {"academic_term": academic_term},
            as_dict=True,
        )

        return data

    except Exception as e:
        frappe.log_error(
            message=f"Error in NBS Sibling Discount Report: {str(e)}",
            title="NBS Sibling Discount Report Error",
        )
        return []


def get_chart(data):
    """Build a bar chart showing total fee vs discount per family."""
    if not data:
        return None

    # Show top 15 families for readability
    top = sorted(data, key=lambda r: r.total_fee_before_discount, reverse=True)[:15]

    labels = [d.guardian_name for d in top]
    fee = [d.total_fee_before_discount for d in top]
    discount = [d.total_discount for d in top]

    return {
        "data": {
            "labels": labels,
            "datasets": [
                {"name": _("Fee Before Discount"), "values": fee},
                {"name": _("Discount"), "values": discount},
            ],
        },
        "type": "bar",
        "colors": ["#5e64ff", "#28a745"],
        "barOptions": {"stacked": False},
        "height": 300,
    }


def get_summary(data):
    """Build report summary cards with overall totals."""
    if not data:
        return []

    total_fee = sum(d.total_fee_before_discount or 0 for d in data)
    total_disc = sum(d.total_discount or 0 for d in data)
    family_count = len(data)
    overall_percent = round(total_disc / total_fee * 100, 2) if total_fee else 0.0

    return [
        {
            "value": family_count,
            "label": _("Families"),
            "datatype": "Int",
            "indicator": "Blue",
        },
        {
            "value": total_fee,
            "label": _("Total Fee Before Discount"),
            "datatype": "Currency",
            "currency": "KWD",
            "indicator": "Blue",
        },
        {
            "value": total_disc,
            "label": _("Total Discount Given"),
            "datatype": "Currency",
            "currency": "KWD",
            "indicator": "Green",
        },
        {
            "value": overall_percent,
            "label": _("Overall Discount %"),
            "datatype": "Percent",
            "indicator": (
                "Green"
                if overall_percent >= 10
                else ("Orange" if overall_percent >= 5 else "Red")
            ),
        },
    ]
