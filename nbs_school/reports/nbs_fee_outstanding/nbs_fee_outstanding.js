// Copyright (c) 2025, Nottingham British School and contributors
// For license information, please see license.txt

frappe.query_reports["NBS Fee Outstanding by Year Group"] = {
	filters: [
		{
			fieldname: "academic_term",
			label: __("Academic Term"),
			fieldtype: "Link",
			options: "Academic Term",
			reqd: 1,
		},
		{
			fieldname: "program",
			label: __("Program / Year Group"),
			fieldtype: "Link",
			options: "Program",
			reqd: 0,
		},
	],

	formatter: function (value, row, column, data, default_formatter) {
		value = default_formatter(value, row, column, data);
		if (column.fieldname === "collection_percent" && data) {
			var pct = data.collection_percent || 0;
			var color = pct >= 80 ? "green" : pct >= 50 ? "orange" : "red";
			value =
				'<span style="color:' +
				color +
				';font-weight:bold">' +
				value +
				"</span>";
		}
		return value;
	},
};
