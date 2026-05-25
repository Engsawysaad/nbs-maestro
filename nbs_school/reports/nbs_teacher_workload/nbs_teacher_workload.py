import frappe
from frappe import _


def execute(filters=None):
    """NBS Teacher Workload Report — Script Report.

    Aggregates Course Schedule data per instructor to show:
        - Teacher Name (from Employee)
        - Employee ID
        - Department
        - Courses Taught (count)
        - Weekly Contact Hours (total, each course schedule entry = 1 hr)
        - Total Students (across all sections)
        - Programs (comma-separated list)
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
            "fieldname": "teacher_name",
            "label": _("Teacher Name"),
            "fieldtype": "Link",
            "options": "Employee",
            "width": 200,
        },
        {
            "fieldname": "employee_id",
            "label": _("Employee ID"),
            "fieldtype": "Data",
            "width": 120,
        },
        {
            "fieldname": "department",
            "label": _("Department"),
            "fieldtype": "Link",
            "options": "Department",
            "width": 180,
        },
        {
            "fieldname": "courses_taught",
            "label": _("Courses Taught"),
            "fieldtype": "Int",
            "width": 140,
        },
        {
            "fieldname": "weekly_contact_hours",
            "label": _("Weekly Contact Hours"),
            "fieldtype": "Int",
            "width": 180,
        },
        {
            "fieldname": "total_students",
            "label": _("Total Students"),
            "fieldtype": "Int",
            "width": 140,
        },
        {
            "fieldname": "programs",
            "label": _("Programs"),
            "fieldtype": "Data",
            "width": 300,
        },
    ]


def get_conditions(filters):
    """Build dynamic WHERE clause fragments and parameter dict from filters."""
    conditions = []
    params = {}

    if filters:
        if filters.get("academic_term"):
            conditions.append("cs.academic_term = %(academic_term)s")
            params["academic_term"] = filters["academic_term"]

        if filters.get("department"):
            conditions.append("emp.department = %(department)s")
            params["department"] = filters["department"]

    return conditions, params


def get_data(filters):
    """Fetch and aggregate teacher workload data from Course Schedule."""
    conditions, params = get_conditions(filters)
    where_clause = " AND ".join(conditions) if conditions else "1=1"

    try:
        data = frappe.db.sql(
            f"""
            SELECT
                emp.employee          AS employee_id,
                emp.employee_name     AS teacher_name,
                emp.department        AS department,
                COUNT(DISTINCT cs.course) AS courses_taught,
                COUNT(cs.name)            AS weekly_contact_hours,
                COALESCE(SUM(sgc.student_count), 0) AS total_students,
                GROUP_CONCAT(DISTINCT crs.course_name SEPARATOR ', ') AS programs
            FROM `tabCourse Schedule` cs
            INNER JOIN `tabInstructor` instr
                ON instr.name = cs.instructor
            INNER JOIN `tabEmployee` emp
                ON emp.name = instr.employee
            LEFT JOIN `tabCourse` crs
                ON crs.name = cs.course
            LEFT JOIN (
                SELECT parent, COUNT(*) AS student_count
                FROM `tabStudent Group Student`
                GROUP BY parent
            ) sgc
                ON sgc.parent = cs.student_group
            WHERE {where_clause}
            GROUP BY emp.employee, emp.employee_name, emp.department
            ORDER BY weekly_contact_hours DESC
            """,
            params,
            as_dict=True,
        )

        return data

    except Exception as e:
        frappe.log_error(
            message=f"Error in NBS Teacher Workload Report: {str(e)}",
            title="NBS Teacher Workload Report Error",
        )
        return []


def get_chart(data):
    """Build a bar chart showing weekly contact hours per teacher (top 15)."""
    if not data:
        return None

    # Top 15 teachers by contact hours
    top = data[:15]
    labels = [d.teacher_name for d in top]
    values = [d.weekly_contact_hours or 0 for d in top]

    return {
        "data": {
            "labels": labels,
            "datasets": [
                {"name": _("Weekly Contact Hours"), "values": values},
            ],
        },
        "type": "bar",
        "colors": ["#5e64ff"],
        "height": 300,
    }


def get_summary(data):
    """Build report summary cards with overall totals."""
    if not data:
        return []

    total_teachers = len(data)
    total_courses = sum(d.courses_taught or 0 for d in data)
    total_hours = sum(d.weekly_contact_hours or 0 for d in data)
    total_students = sum(d.total_students or 0 for d in data)
    avg_hours = round(total_hours / total_teachers, 1) if total_teachers else 0

    return [
        {
            "value": total_teachers,
            "label": _("Total Teachers"),
            "datatype": "Int",
            "indicator": "Blue",
        },
        {
            "value": total_courses,
            "label": _("Total Course Assignments"),
            "datatype": "Int",
            "indicator": "Green",
        },
        {
            "value": total_hours,
            "label": _("Total Weekly Contact Hours"),
            "datatype": "Int",
            "indicator": "Orange",
        },
        {
            "value": total_students,
            "label": _("Total Students"),
            "datatype": "Int",
            "indicator": "Grey",
        },
        {
            "value": avg_hours,
            "label": _("Avg Hours / Teacher"),
            "datatype": "Float",
            "indicator": "Blue",
        },
    ]
