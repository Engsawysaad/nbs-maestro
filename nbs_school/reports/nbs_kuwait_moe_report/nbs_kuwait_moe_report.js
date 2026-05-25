// Copyright (c) 2026, Nottingham British School and contributors
// For license information, please see license.txt

frappe.query_reports["NBS Kuwait MoE Report"] = {
	filters: [
		{
			fieldname: "academic_year",
			label: __("Academic Year"),
			fieldtype: "Link",
			options: "Academic Year",
			reqd: 1,
		},
	],

	formatter: function (value, row, column, data, default_formatter) {
		value = default_formatter(value, row, column, data);
		if (!data) return value;

		// Section headers (indent = 0) — bold in the label column
		if (column.fieldname === "label" && data.indent === 0) {
			value = "<strong>" + value + "</strong>";
		}

		return value;
	},
};
