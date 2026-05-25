// Copyright (c) 2026, Nottingham British School and contributors
// For license information, please see license.txt

frappe.query_reports["NBS IGCSE Entry Summary"] = {
	filters: [
		{
			fieldname: "academic_year",
			label: __("Academic Year"),
			fieldtype: "Link",
			options: "Academic Year",
			reqd: 1,
		},
		{
			fieldname: "exam_session",
			label: __("Exam Session"),
			fieldtype: "Select",
			options: ["", "June", "November"],
			reqd: 0,
		},
	],

	formatter: function (value, row, column, data, default_formatter) {
		value = default_formatter(value, row, column, data);
		if (column.fieldname === "payment_status" && data) {
			var status = data.payment_status || "";
			var color = "grey";
			if (status === "Paid") color = "green";
			else if (status === "Partial") color = "orange";
			else if (status === "Unpaid") color = "red";
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
