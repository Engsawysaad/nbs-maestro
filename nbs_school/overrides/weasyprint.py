import frappe

_patched = False


def patch_weasyprint():
    """Apply once (on first request) to handle Jinja-type print formats.

    The /printview URL route calls ``frappe.utils.weasyprint.get_html()``
    directly, bypassing ``PrintFormat.get_html()`` and the
    ``extend_doctype_class`` override.  This monkey-patch intercepts that
    call so Jinja-type custom formats are rendered via
    ``frappe.render_template()`` instead of crashing inside
    ``PrintFormatGenerator`` (which expects Page Builder layout JSON).
    """
    global _patched
    if _patched:
        return

    from frappe.utils import weasyprint as _weasyprint

    original_get_html = _weasyprint.get_html

    def patched_get_html(doctype, name, print_format, letterhead=None):
        # Resolve the Print Format document (may be passed as name string)
        if isinstance(print_format, str):
            pf = frappe.get_doc("Print Format", print_format)
        else:
            pf = print_format

        # Jinja-type custom formats have format_data = None, crashing
        # PrintFormatGenerator.set_field_renderers().  Render directly.
        if getattr(pf, "print_format_type", None) == "Jinja" and pf.get("html"):
            doc = frappe.get_doc(doctype, name)
            doc.check_permission("print")
            html = frappe.render_template(pf.html, {"doc": doc})
            if pf.get("css"):
                html = f"<style>\n{pf.css}\n</style>\n{html}"
            return html

        # Everything else (Page Builder / standard weasyprint formats)
        return original_get_html(doctype, name, print_format, letterhead)

    _weasyprint.get_html = patched_get_html
    _patched = True
