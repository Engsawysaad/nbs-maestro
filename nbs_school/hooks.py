app_name = "nbs_school"
app_title = "NBS School"
app_publisher = "Nottingham British School"
app_description = "Nottingham British School - Customizations for Education, Accounting, HR, CRM, and Buying modules"
app_email = "it@nottinghambritishschool.edu"
app_license = "MIT"

required_apps = ["frappe", "erpnext"]

# Fixtures
fixtures = [
    {"dt": "Custom Field", "filters": [["module", "=", "NBS School"]]},
    {"dt": "Property Setter", "filters": [["module", "=", "NBS School"]]},
]

# ========================================================
# Document Events (doc_events)
# ========================================================
doc_events = {
    # === CUST-047: Auto-create User Permission on Course Schedule submit ===
    "Course Schedule": {
        "on_submit": "nbs_school.permissions.course_schedule.on_submit_auto_user_permission",
    },
    # === CUST-024: Auto-generate placeholder email for Student ===
    "Student": {
        "before_insert": "nbs_school.student_management.student_email.before_insert_set_email",
        # === CUST-014: Auto-link Guardian on Student update ===
        "on_update": "nbs_school.student_management.guardian_linking.on_update_auto_link_guardian",
    },
    # === CUST-015: Auto-assign Student Groups on Program Enrollment submit ===
    "Program Enrollment": {
        "on_submit": "nbs_school.student_management.student_grouping.on_submit_auto_assign_groups",
    },
    # === CUST-017: Check absence threshold on Attendance submit ===
    "Attendance": {
        "on_submit": "nbs_school.attendance.absence_notification.on_submit_check_absence",
    },
    # === CUST-027: Apply sibling discount on Sales Invoice ===
    "Sales Invoice": {
        "before_validate": "nbs_school.accounting.sibling_discount.before_validate_apply_sibling_discount",
    },
    # === CUST-038: Auto-create enrollment from Opportunity ===
    "Opportunity": {
        "on_update": "nbs_school.crm.auto_enrollment.on_update_opportunity_to_enrollment",
    },
}

# ========================================================
# Permission Hooks
# ========================================================
permission_query_conditions = {
    # === CUST-045: Course Schedule (existing) ===
    "Course Schedule": "nbs_school.permissions.course_schedule.course_schedule_query_conditions",
    # === CUST-045: Student ===
    "Student": "nbs_school.permissions.student.student_query_conditions",
    # === CUST-045: Attendance ===
    "Attendance": "nbs_school.permissions.attendance.attendance_query_conditions",
    # === CUST-045: Assessment Result ===
    "Assessment Result": "nbs_school.permissions.assessment.assessment_query_conditions",
    # === CUST-045: Fee Schedule ===
    "Fee Schedule": "nbs_school.permissions.fee.fee_query_conditions",
    # === CUST-045: Sales Invoice (for fee-related access) ===
    "Sales Invoice": "nbs_school.permissions.fee.fee_query_conditions",
}

has_permission = {
    # === CUST-046: Course Schedule (existing) ===
    "Course Schedule": "nbs_school.permissions.course_schedule.has_course_schedule_permission",
    # === CUST-046: Student ===
    "Student": "nbs_school.permissions.student.has_student_permission",
    # === CUST-046: Attendance ===
    "Attendance": "nbs_school.permissions.attendance.has_attendance_permission",
    # === CUST-046: Assessment Result ===
    "Assessment Result": "nbs_school.permissions.assessment.has_assessment_permission",
    # === CUST-046: Fee Schedule ===
    "Fee Schedule": "nbs_school.permissions.fee.has_fee_permission",
    # === CUST-046: Sales Invoice (for fee-related access) ===
    "Sales Invoice": "nbs_school.permissions.fee.has_fee_permission",
}

# ========================================================
# Scheduled Events
# ========================================================
scheduler_events = {
    # === CUST-028: Daily late fee calculation ===
    "daily": [
        "nbs_school.accounting.late_fees.apply_late_fees_daily",
        # === CUST-017: Daily absence summary ===
        "nbs_school.attendance.absence_notification.daily_absence_summary",
    ],
    # === CUST-026: Termly fee invoice generation (runs 1st of month at 2 AM) ===
    "cron": {
        "0 2 1 * *": [
            "nbs_school.accounting.fee_invoicing.generate_termly_fee_invoices",
        ],
    },
}
