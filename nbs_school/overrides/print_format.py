import frappe
from frappe.model.document import Document


class NBSPrintFormatOverride(Document):
    """Extends PrintFormat.get_html() to handle Jinja-type print formats.

    Frappe v16's weasyprint.PrintFormatGenerator expects Page Builder layout JSON
    (format_data) and crashes with TypeError when format_data is None. Jinja-type
    custom print formats don't have format_data, so this override renders their
    Jinja HTML directly via frappe.render_template(), bypassing the weasyprint path.
    """

    def get_html(self, docname, letterhead=None):
        # For Jinja-type custom formats, render directly — weasyprint crashes
        # on these because format_data is None.
        if self.print_format_type == "Jinja" and self.html:
            doc = frappe.get_doc(self.doc_type, docname)
            doc.check_permission("print")
            html = frappe.render_template(self.html, {"doc": doc})

            # The print format's CSS is stored in a separate `css` field.
            # Include it inline so styling (layout, colors, fonts) renders
            # correctly when the HTML is embedded in a web page.
            if self.css:
                html = f"<style>\n{self.css}\n</style>\n{html}"

            return html

        # For Page Builder / weasyprint formats, use the original path
        return super().get_html(docname, letterhead)
