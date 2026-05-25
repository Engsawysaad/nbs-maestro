// Copyright (c) 2025, Nottingham British School and contributors
// For license information, please see license.txt

frappe.query_reports["NBS Zakat Calculation"] = {
	filters: [
		{
			fieldname: "fiscal_year",
			label: __("Fiscal Year"),
			fieldtype: "Link",
			options: "Fiscal Year",
			reqd: 1,
		},
	],
};
