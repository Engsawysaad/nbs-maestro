app_name = "nbs_school"
app_title = "NBS School"
app_publisher = "Nottingham British School"
app_description = "Nottingham British School - Customizations for Education, Accounting, HR, CRM, and Buying modules"
app_email = "it@nottinghambritishschool.edu"
app_license = "MIT"

required_apps = ["frappe", "erpnext"]

# ========================================================
# Before Request — one-shot patches applied on first request
# ========================================================
before_request = [
    "nbs_school.overrides.weasyprint.patch_weasyprint",
]

# ========================================================
# After Migrate — sync custom fields for CUST-017 et al.
# ========================================================
after_migrate = [
    "nbs_school.attendance.custom_fields.after_migrate",
],
    # === CUST-026: Termly fee invoice generation (runs 1st of month at 2 AM) ===
    "cron": {
        "0 2 1 * *": [
            "nbs_school.accounting.fee_invoicing.generate_termly_fee_invoices",
        ],
    },
}

# ========================================================
# DocType Class Extensions (v16+ mixin-based)
# ========================================================
extend_doctype_class = {
    # Override PrintFormat.get_html() — Jinja-type formats crash weasyprint
    # because they lack format_data (Page Builder layout JSON). This mixin
    # renders their Jinja HTML directly.
    "Print Format": ["nbs_school.overrides.print_format.NBSPrintFormatOverride"],
}

# ========================================================
# Website / Portal Configuration (Section 7)
# ========================================================

# Inject portal CSS on all web pages
app_include_css = [
    "/assets/nbs_school/css/portal.css",
    "/assets/nbs_school/css/portal-rtl.css",
]

# Role-based homepages
role_home_page = {
    "NBS Parent": "parent-dashboard",
    "Student": "student-dashboard",
}

# Website context overrides
website_context = {
    "favicon": "/assets/nbs_school/images/favicon.png",
}

# Website generators (for DocTypes with has_web_view)
website_generators = ["NBS Announcement"]
