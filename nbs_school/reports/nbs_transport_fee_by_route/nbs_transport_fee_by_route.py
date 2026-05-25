import frappe
from frappe import _

def execute(filters=None):
    columns = get_columns()
    data = get_data(filters)
    return columns, data

def get_columns():
    return [
        {"fieldname": "route", "label": _("Route"), "fieldtype": "Data", "width": 200},
        {"fieldname": "student_count", "label": _("Student Count"), "fieldtype": "Int", "width": 120},
        {"fieldname": "fee_per_student", "label": _("Fee per Student (KWD)"), "fieldtype": "Currency", "width": 150, "options": "KWD"},
        {"fieldname": "total_fee", "label": _("Total Fee (KWD)"), "fieldtype": "Currency", "width": 150, "options": "KWD"},
        {"fieldname": "collected", "label": _("Collected (KWD)"), "fieldtype": "Currency", "width": 150, "options": "KWD"},
        {"fieldname": "outstanding", "label": _("Outstanding (KWD)"), "fieldtype": "Currency", "width": 150, "options": "KWD"},
        {"fieldname": "collection_status", "label": _("Collection Status"), "fieldtype": "Data", "width": 130},
    ]

def get_data(filters):
    academic_term = filters.get("academic_term") if filters else None
    if not academic_term:
        return []

    try:
        data = frappe.db.sql("""
            SELECT
                COALESCE(fs.custom_route, fs.title, fs.name) AS route,
                COUNT(DISTINCT si.student) AS student_count,
                AVG(comp.amount) AS fee_per_student,
                SUM(comp.amount) AS total_fee,
                COALESCE(SUM(si.paid_amount), 0) AS collected,
                COALESCE(SUM(si.outstanding_amount), 0) AS outstanding
            FROM `tabFee Structure` fs
            INNER JOIN `tabFee Component` comp ON comp.parent = fs.name
            LEFT JOIN `tabFee Schedule` fsch ON fsch.fee_structure = fs.name
            LEFT JOIN `tabSales Invoice` si ON si.fee_schedule = fsch.name
                AND si.docstatus = 1
            WHERE fs.academic_term = %(academic_term)s
                AND comp.fees_category LIKE %(transport)s
            GROUP BY fs.name
            ORDER BY route
        """, {
            "academic_term": academic_term,
            "transport": "%Transport%"
        }, as_dict=True)

        for row in data:
            row.total_fee = row.total_fee or 0
            row.collected = row.collected or 0
            row.outstanding = row.outstanding or 0
            if row.total_fee <= 0:
                row.collection_status = _("N/A")
            elif row.outstanding <= 0:
                row.collection_status = _("Paid")
            elif row.collected > 0:
                row.collection_status = _("Partial")
            else:
                row.collection_status = _("Unpaid")

        return data
    except Exception as e:
        frappe.log_error(
            message=f"NBS Transport Fee Report error: {str(e)}",
            title="NBS Transport Fee by Route Error"
        )
        return []
