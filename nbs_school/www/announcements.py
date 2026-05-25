import frappe

def get_context(context):
    context.no_cache = 1
    context.title = "Announcements"
    context.show_sidebar = True
    
    context.announcements = frappe.get_all(
        "NBS Announcement",
        filters={"published": 1},
        fields=["title", "content", "publish_date", "priority", "route"],
        order_by="publish_date desc",
        limit=20
    )
