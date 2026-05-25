import frappe
from frappe import _
from frappe.utils.file_manager import save_file
from frappe.utils import now_datetime

# KFTC flat file constants
KFTC_HEADER = "01"
KFTC_DETAIL = "02"
KFTC_TRAILER = "03"
FILE_PREFIX = "WPS"


@frappe.whitelist()
def generate_wps_file(payroll_entry_name: str) -> dict:
    """
    Generate a KFTC-format WPS (Wage Protection System) flat file
    for the given Payroll Entry and attach it as a File document.

    File format (pipe-delimited):
      Header: 01|company|total_amount|count
      Detail: 02|name|civil_id|iban|amount|KWD
      Trailer: 03|total_amount|count

    Args:
        payroll_entry_name: Name of the Payroll Entry document.

    Returns:
        dict with 'file_url' key pointing to the saved File document.
    """
    # 1. Permission guard — HR / Payroll users only
    if not frappe.has_permission("Payroll Entry", "read", payroll_entry_name):
        frappe.throw(
            _("Not permitted to access Payroll Entry {0}").format(payroll_entry_name),
            frappe.PermissionError,
        )

    # 2. Validate & fetch the Payroll Entry
    try:
        payroll_entry = frappe.get_doc("Payroll Entry", payroll_entry_name)
    except frappe.DoesNotExistError:
        frappe.log_error(
            message=f"Payroll Entry '{payroll_entry_name}' not found",
            title="WPS Generation: Payroll Entry Not Found",
        )
        frappe.throw(
            _("Payroll Entry {0} not found").format(payroll_entry_name),
            frappe.DoesNotExistError,
        )

    assert payroll_entry is not None  # guaranteed by throw above on failure

    # 3. Collect salary slips linked to this payroll entry
    salary_slips = frappe.get_all(
        "Salary Slip",
        filters={
            "payroll_entry": payroll_entry_name,
            "docstatus": 1,
            "status": ["!=", "Cancelled"],
        },
        fields=["name", "employee", "net_pay"],
    )

    if not salary_slips:
        frappe.throw(
            _("No submitted Salary Slips found for Payroll Entry {0}").format(
                payroll_entry_name
            ),
            title=_("WPS Generation: No Salary Slips"),
        )

    # 4. Build detail lines & collect totals
    company_name = payroll_entry.company
    detail_lines = []
    total_amount = 0.0
    errors = []

    for slip in salary_slips:
        try:
            employee_name = frappe.db.get_value("Employee", slip.employee, "employee_name")
            civil_id = frappe.db.get_value("Employee", slip.employee, "passport_number")
            iban = frappe.db.get_value("Employee", slip.employee, "bank_account")

            if not civil_id:
                raise ValueError(_("Civil ID (passport_number) is missing"))
            if not iban:
                raise ValueError(_("IBAN (bank_account) is missing"))

            amount = float(slip.net_pay)
            if amount <= 0:
                continue

            detail_lines.append(
                f"{KFTC_DETAIL}|{employee_name or ''}|{civil_id}|{iban}|{amount:.3f}|KWD"
            )
            total_amount += amount

        except Exception as e:
            msg = _("Skipping Salary Slip {0} (Employee {1}): {2}").format(
                slip.name, slip.employee, str(e)
            )
            errors.append(str(msg))
            frappe.log_error(
                message=str(msg),
                title="WPS Generation: Employee Data Error",
            )

    if not detail_lines:
        frappe.throw(
            _("No valid Salary Slips could be processed. {0} errors recorded.").format(
                len(errors)
            ),
            title=_("WPS Generation: All Records Failed"),
        )

    # 5. Assemble the flat file
    count = len(detail_lines)
    header = f"{KFTC_HEADER}|{company_name}|{total_amount:.3f}|{count}"
    trailer = f"{KFTC_TRAILER}|{total_amount:.3f}|{count}"
    file_content = "\n".join([header, *detail_lines, trailer])

    # 6. Save as File attachment on the Payroll Entry
    timestamp = now_datetime().strftime("%Y%m%d_%H%M%S")
    filename = f"{FILE_PREFIX}_{payroll_entry_name}_{timestamp}.txt"

    try:
        file_doc = save_file(
            fname=filename,
            content=file_content.encode("utf-8-sig"),
            dt="Payroll Entry",
            dn=payroll_entry_name,
            folder="Home/Attachments",
            is_private=1,
        )
    except Exception as e:
        frappe.log_error(
            message=f"Failed to save WPS file for Payroll Entry {payroll_entry_name}: {e}",
            title="WPS Generation: File Save Error",
        )
        frappe.throw(
            _("Failed to save WPS file: {0}").format(str(e)),
            title=_("WPS Generation Error"),
        )

    assert file_doc is not None  # guaranteed by throw above on failure

    # 7. Log summary
    summary = (
        f"WPS file generated for Payroll Entry '{payroll_entry_name}': "
        f"{count} employees, total {total_amount:.3f} KWD, "
        f"{len(errors)} records skipped."
    )
    frappe.log_error(message=summary, title="WPS Generation Summary")

    return {"file_url": file_doc.file_url}


@frappe.whitelist()
def validate_wps_data(payroll_entry_name: str) -> dict:
    """
    Validate that all employees in the Payroll Entry have the required
    WPS data (Civil ID / passport_number and IBAN / bank_account).

    Args:
        payroll_entry_name: Name of the Payroll Entry document.

    Returns:
        dict with 'valid' (bool) and 'issues' (list of problem descriptions).
    """
    # 1. Permission guard
    if not frappe.has_permission("Payroll Entry", "read", payroll_entry_name):
        frappe.throw(
            _("Not permitted to access Payroll Entry {0}").format(payroll_entry_name),
            frappe.PermissionError,
        )

    # 2. Validate Payroll Entry exists
    if not frappe.db.exists("Payroll Entry", payroll_entry_name):
        frappe.throw(
            _("Payroll Entry {0} not found").format(payroll_entry_name),
            frappe.DoesNotExistError,
        )

    # 3. Get salary slips
    salary_slips = frappe.get_all(
        "Salary Slip",
        filters={
            "payroll_entry": payroll_entry_name,
            "docstatus": 1,
        },
        fields=["name", "employee"],
    )

    if not salary_slips:
        return {
            "valid": False,
            "issues": [_("No submitted Salary Slips found for this Payroll Entry.")],
        }

    issues = []
    valid_count = 0

    for slip in salary_slips:
        employee_name = frappe.db.get_value("Employee", slip.employee, "employee_name")
        civil_id = frappe.db.get_value("Employee", slip.employee, "passport_number")
        iban = frappe.db.get_value("Employee", slip.employee, "bank_account")
        missing_fields = []

        if not civil_id:
            missing_fields.append(_("Civil ID (passport_number)"))
        if not iban:
            missing_fields.append(_("IBAN (bank_account)"))

        if missing_fields:
            issues.append(
                _("Employee '{0}' ({1}) is missing: {2}").format(
                    employee_name or slip.employee,
                    slip.employee,
                    ", ".join(missing_fields),
                )
            )
        else:
            valid_count += 1

    is_valid = len(issues) == 0

    if not is_valid:
        summary = _(
            "WPS validation for Payroll Entry '{0}': {1} valid, {2} issues found."
        ).format(payroll_entry_name, valid_count, len(issues))
        frappe.log_error(message=summary, title="WPS Validation: Issues Found")

    return {"valid": is_valid, "issues": issues}
