import frappe
from frappe import _


def execute(filters=None):
    """NBS Fee Outstanding by Year Group — Script Report.

    Groups fee invoice data by Program (year group) and computes:
        - Student count
        - Total invoiced (KWD)
        - Total collected (KWD)
        - Outstanding balance (KWD)
        - Collection percentage
    """
    columns = get_columns()
    data = get_data(filters)
    chart = get_chart(data)
    report_summary = get_summary(data)
    return columns, data, None, chart, report_summary


def get_columns():
    """Return report column definitions."""
    return [
        {
            "fieldname": "program",
            "label": _("Program / Year Group"),
            "fieldtype": "Link",
            "options": "Program",
            "width": 220,
        },
        {
            "fieldname": "student_count",
            "label": _("Student Count"),
            "fieldtype": "Int",
            "width": 130,
        },
        {
            "fieldname": "total_invoiced",
            "label": _("Total Invoiced"),
            "fieldtype": "Currency",
            "options": "KWD",
            "width": 150,
        },
        {
            "fieldname": "total_collected",
            "label": _("Total Collected"),
            "fieldtype": "Currency",
            "options": "KWD",
            "width": 150,
        },
        {
            "fieldname": "total_outstanding",
            "label": _("Outstanding"),
            "fieldtype": "Currency",
            "options": "KWD",
            "width": 150,
        },
        {
            "fieldname": "collection_percent",
            "label": _("Collection %"),
            "fieldtype": "Percent",
            "width": 120,
        },
    ]


def get_conditions(filters):
    """Build dynamic WHERE clause fragments and parameter dict from filters."""
    conditions = []
    params = {}

    if filters:
        if filters.get("academic_term"):
            conditions.append("si.academic_term = %(academic_term)s")
            params["academic_term"] = filters["academic_term"]

        if filters.get("program"):
            conditions.append("pe.program = %(program)s")
            params["program"] = filters["program"]

    return conditions, params


def get_data(filters):
    """Fetch and aggregate fee invoice data grouped by Program."""
    conditions, params = get_conditions(filters)
    where_clause = " AND ".join(conditions) if conditions else "1=1"

    try:
        data = frappe.db.sql(
            f"""
            SELECT
                pe.program,
                COUNT(DISTINCT si.student) AS student_count,
                COALESCE(SUM(si.grand_total), 0) AS total_invoiced,
                COALESCE(SUM(si.outstanding_amount), 0) AS total_outstanding
            FROM `tabSales Invoice` si
            INNER JOIN `tabProgram Enrollment` pe
                ON pe.student = si.student
                AND pe.academic_term = si.academic_term
                AND pe.docstatus = 1
            WHERE si.docstatus = 1
                AND si.naming_series LIKE 'NBS-INV-%'
                AND si.student IS NOT NULL
                AND si.academic_term IS NOT NULL
                AND {where_clause}
            GROUP BY pe.program
            ORDER BY pe.program
            """,
            params,
            as_dict=True,
        )

        for row in data:
            row.total_collected = row.total_invoiced - row.total_outstanding
            if row.total_invoiced:
                row.collection_percent = round(
                    (row.total_collected / row.total_invoiced) * 100, 2
                )
            else:
                row.collection_percent = 0.0

        return data

    except Exception as e:
        frappe.log_error(
            message=f"Error in NBS Fee Outstanding Report: {str(e)}",
            title="NBS Fee Outstanding Report Error",
        )
        return []


def get_chart(data):
    """Build a stacked bar chart showing invoiced, collected, and outstanding by program."""
    if not data:
        return None

    labels = [d.program for d in data]
    invoiced = [d.total_invoiced for d in data]
    collected = [d.total_collected for d in data]
    outstanding = [d.total_outstanding for d in data]

    return {
        "data": {
            "labels": labels,
            "datasets": [
                {"name": _("Invoiced"), "values": invoiced},
                {"name": _("Collected"), "values": collected},
                {"name": _("Outstanding"), "values": outstanding},
            ],
        },
        "type": "bar",
        "colors": ["#5e64ff", "#28a745", "#dc3545"],
        "barOptions": {"stacked": True},
        "height": 300,
    }


def get_summary(data):
    """Build report summary cards with overall totals."""
    if not data:
        return []

    total_invoiced = sum(d.total_invoiced or 0 for d in data)
    total_collected = sum(d.total_collected or 0 for d in data)
    total_outstanding = sum(d.total_outstanding or 0 for d in data)
    overall_percent = (
        round((total_collected / total_invoiced) * 100, 2)
        if total_invoiced
        else 0.0
    )

    return [
        {
            "value": total_invoiced,
            "label": _("Total Invoiced"),
            "datatype": "Currency",
            "currency": "KWD",
            "indicator": "Blue",
        },
        {
            "value": total_collected,
            "label": _("Total Collected"),
            "datatype": "Currency",
            "currency": "KWD",
            "indicator": "Green",
        },
        {
            "value": total_outstanding,
            "label": _("Total Outstanding"),
            "datatype": "Currency",
            "currency": "KWD",
            "indicator": "Red" if total_outstanding > 0 else "Grey",
        },
        {
            "value": overall_percent,
            "label": _("Overall Collection %"),
            "datatype": "Percent",
            "indicator": (
                "Green"
                if overall_percent >= 80
                else ("Orange" if overall_percent >= 50 else "Red")
            ),
        },
    ]
