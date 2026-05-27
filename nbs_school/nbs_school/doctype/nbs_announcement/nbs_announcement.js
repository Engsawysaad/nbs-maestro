frappe.ui.form.on("NBS Announcement", {
    refresh: function(frm) {
        if (!frm.doc.publish_date) {
            frm.set_value("publish_date", frappe.datetime.nowdate());
        }
    }
});
