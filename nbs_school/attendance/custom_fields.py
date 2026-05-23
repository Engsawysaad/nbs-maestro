"""
CUST-017: Custom fields for absence notification configuration.

Adds two fields to Education Settings:
- ``absence_alert_threshold`` (Int, default 3)
- ``default_notification_recipient`` (Data / Email)

Called from the ``after_migrate`` hook so the fields are always present
on existing sites after an app update.
"""

import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields


CUSTOM_FIELDS = {
    "Education Settings": [
        {
            "fieldname": "default_notification_recipient",
            "label": "Default Notification Recipient",
            "fieldtype": "Data",
            "options": "Email",
            "description": (
                "Email address for the daily absence summary and other "
                "automated notifications sent by the NBS School app."
            ),
            "insert_after": "academic_year",
            "module": "NBS School",
        },
        {
            "fieldname": "absence_alert_threshold",
            "label": "Absence Alert Threshold",
            "fieldtype": "Int",
            "default": "3",
            "description": (
                "Number of consecutive absence days that triggers an alert "
                "to the student's guardian(s)."
            ),
            "insert_after": "default_notification_recipient",
            "module": "NBS School",
        },
    ]
}


def after_migrate():
    """Called by the ``after_migrate`` hook to create / update custom fields."""
    create_custom_fields(CUSTOM_FIELDS, ignore_validate=True)
    frappe.logger().info("NBS School: absence notification custom fields synced.")
