frappe.query_reports["NBS Transport Fee by Route"] = {
    "filters": [
        {
            "fieldname": "academic_term",
            "label": __("Academic Term"),
            "fieldtype": "Link",
            "options": "Academic Term",
            "reqd": 1,
        },
    ],
};
