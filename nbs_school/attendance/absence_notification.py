import frappe
from frappe import _
from frappe.utils import today


def on_submit_check_absence(doc, method):
    """
    CUST-017: Automated absence notification.

    Triggered on Attendance `on_submit` when status is "Absent".
    Checks if the student has exceeded the consecutive absence threshold
    (default: 3 consecutive days) and sends a notification to the
    guardian(s) on file.

    Also logs an entry for the daily absence summary scheduler.
    """
    if doc.status != "Absent":
        return

    if not doc.student:
        return

    # Check consecutive absences
    consecutive = _count_consecutive_absences(doc.student, doc.attendance_date)
    if consecutive >= 3:
        _send_absence_alert(doc, consecutive)

    # Log attendance event for daily batch processing
    _log_absence_event(doc)


def _count_consecutive_absences(student, attendance_date):
    """Count consecutive absence days ending at attendance_date."""
    from datetime import datetime, timedelta

    try:
        current_date = datetime.strptime(str(attendance_date), "%Y-%m-%d")
    except (ValueError, TypeError):
        return 0

    count = 0
    for i in range(30):  # Check up to 30 days back
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
        # If no record (weekend/holiday), continue without counting

    return count


def _send_absence_alert(doc, consecutive_days):
    """
    Send absence notification to guardians.
    Uses Frappe's email queue system. SMS integration can be added later.
    """
    guardians = frappe.get_all(
        "Guardian Student",
        filters={"student": doc.student},
        fields=["parent"],
    )

    if not guardians:
        return

    student_name = frappe.get_value("Student", doc.student, "student_name") or doc.student

    for g in guardians:
        guardian_email = frappe.get_value("Guardian", g.parent, "email_address")
        guardian_name = frappe.get_value("Guardian", g.parent, "guardian_name") or "Guardian"

        if not guardian_email:
            continue

        subject = _("Absence Alert: {0} - {1} consecutive days").format(
            student_name, consecutive_days
        )
        message = _(
            """
            <h3>Attendance Alert</h3>
            <p>Dear {0},</p>
            <p>This is to notify you that <strong>{1}</strong> has been marked absent
            for <strong>{2} consecutive day(s)</strong> as of {3}.</p>
            <p>Please ensure the school is notified of the reason for absence.</p>
            <hr>
            <p><small>Nottingham British School - Automated Attendance System</small></p>
            """
        ).format(guardian_name, student_name, consecutive_days, str(doc.attendance_date))

        try:
            frappe.sendmail(
                recipients=[guardian_email],
                subject=subject,
                message=message,
                reference_doctype="Attendance",
                reference_name=doc.name,
            )
        except Exception as e:
            frappe.log_error(
                message=f"Failed to send absence alert to {guardian_email} for Student {doc.student}: {e}",
                title="NBS Absence Notification Error",
            )


def _log_absence_event(doc):
    """Log attendance event for daily summary processing."""
    if not frappe.db.exists("DocType", "Attendance Log"):  # Use a custom log or standard Error Log
        pass  # Falls back to Error Log tracking

    frappe.log_error(
        message=f"Attendance: {doc.student} | Date: {doc.attendance_date} | Status: {doc.status}",
        title="NBS Attendance Event",
    )


def daily_absence_summary():
    """
    Scheduled job: Sends a daily summary of all absences to designated staff.

    To be registered in hooks.py as a scheduler_event.
    """
    yesterday = frappe.utils.add_days(today(), -1)

    absent_records = frappe.get_all(
        "Attendance",
        filters={
            "attendance_date": yesterday,
            "status": "Absent",
            "docstatus": 1,
        },
        fields=["student", "student_name", "course_schedule"],
    )

    if not absent_records:
        return

    summary_lines = []
    for r in absent_records:
        student_name = r.student_name or r.student
        summary_lines.append(f"- {student_name}")

    summary = _(
        """
        <h3>Daily Absence Summary - {0}</h3>
        <p>Total absent students: <strong>{1}</strong></p>
        <ul>{2}</ul>
        """
    ).format(yesterday, len(absent_records), "".join(summary_lines))

    # Send to configured recipients
    notification_recipients = frappe.db.get_single_value(
        "Education Settings", "default_notification_recipient"
    )
    recipients = [notification_recipients] if notification_recipients else []

    if recipients:
        frappe.sendmail(
            recipients=recipients,
            subject=_("NBS Daily Absence Summary - {0}").format(yesterday),
            message=summary,
        )
