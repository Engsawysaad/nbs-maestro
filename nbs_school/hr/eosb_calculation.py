import frappe
from frappe import _
from frappe.utils import date_diff, nowdate, getdate

# ============================================================
# EOSB Constants — Kuwait Labour Law
# ============================================================
EOSB_DAYS_YEAR_1_5 = 15      # First 5 years: 15 days basic salary per year
EOSB_DAYS_YEAR_5plus = 20    # After 5 years:  20 days basic salary per year
CALC_DAYS = 365              # Days used per year in daily-rate calculation


def _get_years_of_service(from_date, to_date=None):
    """Calculate years of service between two dates as a float.

    Args:
        from_date: Start date (typically date_of_joining).
        to_date:   End date (defaults to today if not provided).

    Returns:
        float: Number of years (e.g. 8.5 for 8 years 6 months).
    """
    if to_date is None:
        to_date = nowdate()
    days = date_diff(getdate(to_date), getdate(from_date))
    return days / CALC_DAYS


@frappe.whitelist()
def calculate_eosb(employee, calculation_date=None):
    """Calculate End of Service Benefit for an employee under Kuwait Labour Law.

    Rules:
        - First 5 years → 15 days basic salary per year
        - After 5 years  → 20 days basic salary per year
        - Daily rate     = basic_salary / CALC_DAYS × days_per_year × years_in_band

    Args:
        employee:         Employee ID (e.g. "EMP-00001").
        calculation_date: Date as of which to calculate (defaults to today).

    Returns:
        dict with keys:
            employee, employee_name, date_of_joining, years_of_service,
            basic_salary, total_eosb, calculation_date, breakdown
    """
    # 1. Default calculation date
    if not calculation_date:
        calculation_date = nowdate()

    # 2. Validate employee exists and is active
    emp_data = frappe.db.get_value(
        "Employee",
        employee,
        ["employee_name", "date_of_joining", "status"],
        as_dict=True,
    )
    if not emp_data:
        frappe.throw(
            _("Employee {0} not found").format(employee),
            frappe.DoesNotExistError,
        )

    if emp_data.status != "Active":
        frappe.throw(
            _("Employee {0} is not Active (current status: {1})").format(
                employee, emp_data.status
            ),
            title=_("EOSB Calculation"),
        )

    # 3. Get basic salary from latest Salary Structure Assignment
    basic_salary = frappe.db.get_value(
        "Salary Structure Assignment",
        {
            "employee": employee,
            "docstatus": 1,
            "from_date": ["<=", calculation_date],
        },
        "base",
        order_by="from_date desc",
    )
    if not basic_salary:
        frappe.throw(
            _(
                "No active Salary Structure Assignment found for Employee {0}"
                " as of {1}"
            ).format(employee, calculation_date),
            title=_("EOSB Calculation"),
        )

    basic_salary = float(basic_salary)

    # 4. Calculate years of service
    date_of_joining = emp_data.date_of_joining
    years_of_service = _get_years_of_service(date_of_joining, calculation_date)

    if years_of_service <= 0:
        frappe.throw(
            _("Employee {0} joined on {1} — no completed service years as of {2}").format(
                employee, date_of_joining, calculation_date
            ),
            title=_("EOSB Calculation"),
        )

    # 5. Calculate EOSB by year bands
    breakdown = []
    total_eosb = 0.0

    # Band 1: First 5 years
    band1_years = min(5, years_of_service)
    if band1_years > 0:
        band1_amount = (basic_salary / CALC_DAYS) * EOSB_DAYS_YEAR_1_5 * band1_years
        breakdown.append({
            "band": "1-5",
            "years": round(band1_years, 2),
            "days_per_year": EOSB_DAYS_YEAR_1_5,
            "amount": round(band1_amount, 3),
        })
        total_eosb += band1_amount

    # Band 2: After 5 years
    band2_years = max(0, years_of_service - 5)
    if band2_years > 0:
        band2_amount = (basic_salary / CALC_DAYS) * EOSB_DAYS_YEAR_5plus * band2_years
        breakdown.append({
            "band": "5+",
            "years": round(band2_years, 2),
            "days_per_year": EOSB_DAYS_YEAR_5plus,
            "amount": round(band2_amount, 3),
        })
        total_eosb += band2_amount

    return {
        "employee": employee,
        "employee_name": emp_data.employee_name,
        "date_of_joining": str(date_of_joining),
        "years_of_service": round(years_of_service, 2),
        "basic_salary": basic_salary,
        "total_eosb": round(total_eosb, 3),
        "calculation_date": calculation_date,
        "breakdown": breakdown,
    }


@frappe.whitelist()
def batch_calculate_eosb(department=None):
    """Calculate EOSB for all active employees, with optional department filter.

    Iterates every active Employee (optionally filtered by department),
    calls :func:`calculate_eosb` for each, and collects results. Errors
    are logged via ``frappe.log_error`` and returned inline so the caller
    can review which employees failed.

    Args:
        department: Optional department name to restrict the calculation.

    Returns:
        dict with:
            results (list): Successful EOSB result dicts.
            errors  (list): Error message strings for employees that failed.
    """
    filters = {"status": "Active"}
    if department:
        filters["department"] = department

    employees = frappe.get_all("Employee", filters=filters, pluck="name")

    if not employees:
        frappe.msgprint(_("No active employees found."))
        return {"results": [], "errors": []}

    results = []
    errors = []

    for emp in employees:
        try:
            result = calculate_eosb(employee=emp)
            results.append(result)
        except Exception as e:
            error_msg = _("Error calculating EOSB for Employee {0}: {1}").format(emp, str(e))
            errors.append(str(error_msg))
            frappe.log_error(
                message=error_msg,
                title="EOSB Batch Calculation Error",
            )

    return {"results": results, "errors": errors}
