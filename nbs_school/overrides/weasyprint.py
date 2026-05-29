import frappe

_patched = False


def _render_jinja(doctype, name, print_format):
    """Render a Jinja-type print format to HTML (shared by get_html + download_pdf)."""
    if isinstance(print_format, str):
        pf = frappe.get_doc("Print Format", print_format)
    else:
        pf = print_format

    if getattr(pf, "print_format_type", None) != "Jinja" or not pf.get("html"):
        return None  # not a Jinja custom format

    doc = frappe.get_doc(doctype, name)
    doc.check_permission("print")
    html = frappe.render_template(pf.html, {"doc": doc})
    if pf.get("css"):
        html = f"<style>\n{pf.css}\n</style>\n{html}"
    return html


def patch_weasyprint():
    """Apply once (on first request) to handle Jinja-type print formats.

    Frappe v16's weasyprint ``PrintFormatGenerator`` expects Page Builder
    layout JSON (``format_data``).  Jinja-type custom print formats have
    ``format_data = None``, causing ``TypeError`` inside
    ``set_field_renderers()``.

    Two entry points in ``frappe.utils.weasyprint`` create
    ``PrintFormatGenerator`` directly:

    * ``get_html()``         – used by the ``/printview`` route
    * ``download_pdf()``     – used by the "Export as PDF" button

    This monkey-patch intercepts both so Jinja formats are rendered via
    ``frappe.render_template()`` instead.
    """
    global _patched
    if _patched:
        return

    from frappe.utils import weasyprint as _weasyprint

    # ── patch get_html (used by /printview) ──────────────────────────
    original_get_html = _weasyprint.get_html

    def patched_get_html(doctype, name, print_format, letterhead=None):
        html = _render_jinja(doctype, name, print_format)
        if html is not None:
            return html
        return original_get_html(doctype, name, print_format, letterhead)

    _weasyprint.get_html = patched_get_html

    # ── patch download_pdf (used by "Export as PDF") ─────────────────
    original_download_pdf = _weasyprint.download_pdf

    def patched_download_pdf(doctype, name, print_format, letterhead=None):
        html = _render_jinja(doctype, name, print_format)
        if html is not None:
            # Convert rendered HTML to PDF via weasyprint
            import weasyprint
            pdf = weasyprint.HTML(string=html).write_pdf()
            frappe.response["filename"] = f"{name}.pdf"
            frappe.response["filecontent"] = pdf
            frappe.response["type"] = "download"
            return pdf
        return original_download_pdf(doctype, name, print_format, letterhead)

    # Register in Frappe's whitelist set so API handler allows the call.
    # Frappe's is_whitelisted() checks "method not in whitelisted" (a set of
    # function objects), not a function attribute — so we must add our
    # replacement to the set explicitly.
    patched_download_pdf.whitelisted = True
    from frappe import whitelisted as _whitelisted_set, guest_methods as _guest_methods_set
    _whitelisted_set.add(patched_download_pdf)
    if original_download_pdf in _guest_methods_set:
        _guest_methods_set.add(patched_download_pdf)

    _weasyprint.download_pdf = patched_download_pdf

    _patched = True
