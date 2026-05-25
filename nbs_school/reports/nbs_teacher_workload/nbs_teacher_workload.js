// Copyright (c) 2025, Nottingham British School and contributors
// For license information, please see license.txt

frappe.query_reports["NBS Teacher Workload Report"] = {
	filters: [
		{
			fieldname: "academic_term",
			label: __("Academic Term"),
			fieldtype: "Link",
			options: "Academic Term",
			reqd: 1,
		},
		{
			fieldname: "department",
			label: __("Department"),
			fieldtype: "Link",
			options: "Department",
			reqd: 0,
		},
	],
};
