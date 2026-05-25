// Copyright (c) 2025, Nottingham British School and contributors
// For license information, please see license.txt

frappe.query_reports["NBS Sibling Discount"] = {
	filters: [
		{
			fieldname: "academic_term",
			label: __("Academic Term"),
			fieldtype: "Link",
			options: "Academic Term",
			reqd: 1,
		},
	],

	formatter: function (value, row, column, data, default_formatter) {
		value = default_formatter(value, row, column, data);
		if (column.fieldname === "discount_percent" && data) {
			var pct = data.discount_percent || 0;
			var color = pct >= 10 ? "green" : pct >= 5 ? "orange" : "red";
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
