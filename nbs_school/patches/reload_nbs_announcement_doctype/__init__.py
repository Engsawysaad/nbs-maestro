import frappe


def execute():
    """
    CUST-NBS: Reload NBS Announcement DocType after directory rename.

    The previous patch (ensure_nbs_announcement_doctype) called
    frappe.reload_doc() but the DocType JSON lived under the plural
    directory name "doctypes/". Frappe v16 (specifically
    IMPORTABLE_DOCTYPES in frappe/model/sync.py) scans the singular
    directory "doctype/" when syncing DocTypes.

    The directory has been renamed from:
        nbs_school/doctypes/nbs_announcement/
    to:
        nbs_school/doctype/nbs_announcement/

    This patch forces a fresh reload from the correct path.
    Safe to re-run — reload_doc is idempotent.
    """
    MODULE_NAME = "NBS School"
    DOCTYPE_NAME = "NBS Announcement"

    if not frappe.db.exists("Module Def", MODULE_NAME):
        frappe.log_error(
            message=f"Module Def '{MODULE_NAME}' does not exist — skipping reload",
            title="NBS DocType Reload Skipped",
        )
        return

    try:
        frappe.reload_doc(
            frappe.scrub(MODULE_NAME),  # "nbs_school"
            "doctype",
            frappe.scrub(DOCTYPE_NAME),  # "nbs_announcement"
        )
        frappe.db.commit()

        frappe.log_error(
            message=f"Successfully reloaded DocType '{DOCTYPE_NAME}' from renamed directory",
            title="NBS DocType Reloaded",
        )
    except Exception as e:
        frappe.log_error(
            message=f"Failed to reload DocType '{DOCTYPE_NAME}': {e}",
            title="NBS DocType Reload Error",
        )
        raise
