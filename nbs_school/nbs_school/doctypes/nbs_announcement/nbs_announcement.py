import frappe
from frappe.website.website_generator import WebsiteGenerator

class NBSAnnouncement(WebsiteGenerator):
    def get_context(self, context):
        context.no_cache = 1
        context.title = self.title
        context.show_sidebar = True
        context.parents = [{"name": "Announcements", "route": "/announcements"}]
