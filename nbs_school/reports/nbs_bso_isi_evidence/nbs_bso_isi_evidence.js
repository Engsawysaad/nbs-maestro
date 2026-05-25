// Copyright (c) 2026, Nottingham British School and contributors
// For license information, please see license.txt

frappe.query_reports["NBS BSO/ISI Evidence Report"] = {
	filters: [
		{
			fieldname: "academic_year",
			label: __("Academic Year"),
			fieldtype: "Link",
			options: "Academic Year",
			reqd: 1,
		},
		{
			fieldname: "inspection_criterion",
			label: __("Inspection Criterion"),
			fieldtype: "Select",
			options: [
				"",
				"Leadership and Management",
				"Quality of Teaching",
				"Personal Development",
				"Outcomes for Students",
				"Safeguarding",
				"Curriculum",
				"Assessment",
			],
			reqd: 0,
		},
	],
};
