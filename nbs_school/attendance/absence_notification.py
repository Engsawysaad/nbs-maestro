import frappe
from frappe import _
from frappe.utils import today


def on_submit_check_absence(doc, method):
    """
    CUST-017: Automated absence notification.

    Triggered on Attendance `on_submit` when status is 'Absent'.
    Checks if the student has exceeded the configurable consecutive absence threshold
    (default: 3) and sends an email alert to guardian(s).

    UAT ref: UAT-EDU-008 / FR-EDU-008
    """
    if doc.status != "Absent":
        return
    if not doc.student:
        return

    threshold = _get_absence_threshold()

    consecutive = _count_consecutive_absences(doc.student, doc.attendance_date)
    if consecutive >= threshold:
        _send_absence_alert(doc, consecutive)


def _get_absence_threshold():
    """
    Read the configurable consecutive-absence threshold from Education Settings.
    Falls back to 3 if the custom field is missing or not set.
    """
    return (
        frappe.db.get_single_value("Education Settings", "absence_alert_threshold")
        or 3
    )


def _count_consecutive_absences(student, attendance_date):
    """
    Count consecutive 'Absent' days ending at (and including) attendance_date.

    Scans backward day-by-day up to 30 days.  Stops counting when a 'Present'
    record is found.  Days with no Attendance record (e.g. weekends, holidays)
    are skipped without breaking the streak.
    """
    from datetime import datetime, timedelta

    try:
        current_date = datetime.strptime(str(attendance_date), "%Y-%m-%d")
    except (ValueError, TypeError):
        return 0

    count = 0
    for i in range(30):
        check_date = current_date - timedelta(days=i)
        date_str = check_date.strftime("%Y-%m-%d")

        status = frappe.get_value(
            "Attendance",
            filters={
                "student": student,
                "attendance_date": date_str,
                "docstatus": 1,
            },
            fieldname="status",
        )

        if status == "Absent":
            count += 1
        elif status == "Present":
            break
        # No record (weekend/holiday) → continue scanning without counting

    return count


def _send_absence_alert(doc, consecutive_days):
    """
    Send an email absence notification to every guardian linked to the student.

    Collects guardian emails from:
      1. Student's own ``guardians`` child table (Student Guardian)
      2. Reverse lookup via Guardian's ``Guardian Student`` child table

    The email is queued via Frappe's Email Queue (non-blocking).
    """
    guardian_emails = _get_guardian_emails(doc.student)
    if not guardian_emails:
        return

    student_name = (
        frappe.get_value("Student", doc.student, "student_name") or doc.student
    )

    subject = _("Absence Alert: {0} — {1} consecutive day(s)").format(
        student_name, consecutive_days
    )
    message = _(
        """
        <h3>Attendance Alert</h3>
        <p>Dear Guardian,</p>
        <p>This is to notify you that <strong>{0}</strong> has been marked absent
        for <strong>{1} consecutive day(s)</strong> as of {2}.</p>
        <p>Please ensure the school is notified of the reason for absence.</p>
        <hr>
        <p><small>Nottingham British School — Automated Attendance System</small></p>
        """
    ).format(student_name, consecutive_days, str(doc.attendance_date))

    for email in guardian_emails:
        try:
            frappe.sendmail(
                recipients=[email],
                subject=subject,
                message=message,
                reference_doctype="Attendance",
                reference_name=doc.name,
            )
        except Exception as e:
            frappe.log_error(
                message=f"Failed to send absence alert to {email} "
                f"for Student {doc.student}: {e}",
                title="NBS Absence Notification Error",
            )


def _get_guardian_emails(student):
    """
    Return a deduplicated list of guardian email addresses for *student*.

    Two sources are queried:
    - **Student → Guardian** (Student's ``guardians`` child table)
    - **Guardian → Student** (Guardian's ``Guardian Student`` child table)

    Using both directions ensures no linked guardian is missed regardless
    of which side of the relationship was populated first.
    """
    emails = set()

    # --- Source 1: Student's own child table --------------------------------
    student_doc = frappe.get_cached_doc("Student", student)
    for guardian_row in student_doc.get("guardians") or []:
        if guardian_row.get("guardian"):
            email = frappe.get_value(
                "Guardian", guardian_row.guardian, "email_address"
            )
            if email:
                emails.add(email.strip())

    # --- Source 2: Reverse lookup via Guardian Student child table ----------
    guardian_links = frappe.get_all(
        "Guardian Student",
        filters={"student": student},
        fields=["parent"],
    )
    for g in guardian_links:
        email = frappe.get_value("Guardian", g.parent, "email_address")
        if email:
            emails.add(email.strip())

    return list(emails)


def daily_absence_summary():
    """
    Scheduled job (``daily``): sends a summary of yesterday's absences to the
    configured notification recipient.

    Recipient is read from ``Education Settings.default_notification_recipient``.
    If the field is empty, the job silently exits.
    """
    yesterday = frappe.utils.add_days(today(), -1)

    absent_records = frappe.get_all(
        "Attendance",
        filters={
            "attendance_date": yesterday,
            "status": "Absent",
            "docstatus": 1,
        },
        fields=["student", "student_name"],
    )

    if not absent_records:
        return

    recipient = frappe.db.get_single_value(
        "Education Settings", "default_notification_recipient"
    )
    if not recipient:
        return

    summary_lines = "\n".join(
        "- {}".format(r.student_name or r.student) for r in absent_records
    )

    message = _(
        """
        <h3>Daily Absence Summary — {0}</h3>
        <p>Total absent students: <strong>{1}</strong></p>
        <ul>{2}</ul>
        """
    ).format(yesterday, len(absent_records), summary_lines)

    frappe.sendmail(
        recipients=[recipient],
        subject=_("NBS Daily Absence Summary — {0}").format(yesterday),
        message=message,
    )
