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

# Document events for auto-creating User Permissions on Course Schedule submit
doc_events = {
    "Course Schedule": {
        "on_submit": "nbs_school.permissions.course_schedule.on_submit_auto_user_permission"
    }
}

# Permission hooks
permission_query_conditions = {
    "Course Schedule": "nbs_school.permissions.course_schedule.course_schedule_query_conditions"
}

has_permission = {
    "Course Schedule": "nbs_school.permissions.course_schedule.has_course_schedule_permission"
}
