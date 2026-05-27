import frappe


def execute():
    """
    CUST-NBS: Ensure NBS Announcement DocType exists in the database.

    The "NBS School" Module Def may not exist in the database if the app
    was installed before the module was defined, or if it was lost during
    a site restore. Without the Module Def, Frappe's DocType sync phase
    skips this app entirely (no "Updating DocTypes for nbs_school" line),
    because it reads modules from the cached `tabModule Def` table rather
    than from `modules.txt`.

    This patch:
    1. Creates the "NBS School" Module Def if missing.
    2. Reloads the NBS Announcement DocType from its JSON definition.
    """
    MODULE_NAME = "NBS School"
    APP_NAME = "nbs_school"
    DOCTYPE_NAME = "NBS Announcement"

    # Step 1: Ensure Module Def exists in the database
    if not frappe.db.exists("Module Def", MODULE_NAME):
        module_def = frappe.get_doc(
            {
                "doctype": "Module Def",
                "module_name": MODULE_NAME,
                "app_name": APP_NAME,
            }
        )
        module_def.insert(ignore_permissions=True)
        frappe.db.commit()

        frappe.log_error(
            message=f"Created Module Def '{MODULE_NAME}' for app '{APP_NAME}'",
            title="NBS Module Def Created",
        )
    else:
        frappe.log_error(
            message=f"Module Def '{MODULE_NAME}' already exists",
            title="NBS Module Def Check",
        )

    # Step 2: Reload the DocType from its JSON definition
    try:
        frappe.reload_doc(
            frappe.scrub(MODULE_NAME),  # "nbs_school"
            "doctype",
            frappe.scrub(DOCTYPE_NAME),  # "nbs_announcement"
        )
        frappe.db.commit()

        frappe.log_error(
            message=f"Successfully reloaded DocType '{DOCTYPE_NAME}'",
            title="NBS DocType Synced",
        )
    except Exception as e:
        frappe.log_error(
            message=f"Failed to reload DocType '{DOCTYPE_NAME}': {e}",
            title="NBS DocType Sync Error",
        )
        frappe.throw(f"NBS-ANN: Failed to sync DocType '{DOCTYPE_NAME}': {e}")
