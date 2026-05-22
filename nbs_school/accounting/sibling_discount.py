import frappe
from frappe import _


def before_validate_apply_sibling_discount(doc, method):
    """
    CUST-027: Sibling discount engine.

    Triggered on Sales Invoice `before_validate`. Checks the Guardian
    associated with the Student and counts enrolled siblings to
    determine the tiered discount:
    - 1st child: 0% (no discount)
    - 2nd child: 10% discount
    - 3rd+ child: 15% discount

    Requires:
    - Student linked to a Guardian via Guardian Student child table
    - Discount is applied to the base total before taxes
    """
    if doc.is_return or doc.docstatus != 0:
        return

    if not doc.get("student"):
        return

    student = doc.get("student")
    guardian = _find_primary_guardian(student)
    if not guardian:
        return

    sibling_count = _count_enrolled_siblings(guardian, student)
    if sibling_count < 1:
        return

    discount_percentage = _get_discount_rate(sibling_count)
    if discount_percentage <= 0:
        return

    _apply_discount(doc, discount_percentage, guardian)


def _find_primary_guardian(student):
    """Find the primary guardian for a student."""
    guardians = frappe.get_all(
        "Guardian Student",
        filters={"student": student},
        fields=["parent"],
        order_by="idx asc",
        limit=1,
    )
    return guardians[0].parent if guardians else None


def _count_enrolled_siblings(guardian, exclude_student):
    """
    Count other enrolled students under the same guardian,
    excluding the current student.
    """
    siblings = frappe.get_all(
        "Guardian Student",
        filters={"parent": guardian, "student": ["!=", exclude_student]},
        fields=["student"],
    )

    count = 0
    for s in siblings:
        # Verify they have an active Program Enrollment
        is_active = frappe.get_all(
            "Program Enrollment",
            filters={
                "student": s.student,
                "docstatus": 1,
            },
            limit=1,
        )
        if is_active:
            count += 1

    return count


def _get_discount_rate(sibling_count):
    """
    Determine discount percentage based on sibling order.
    - 1st enrolled sibling (count=0, no discount)
    - 2nd enrolled sibling (count=1): 10%
    - 3rd+ enrolled sibling (count>=2): 15%
    """
    if sibling_count >= 2:
        return 15.0
    elif sibling_count == 1:
        return 10.0
    return 0.0


def _apply_discount(doc, percentage, guardian):
    """Apply the discount to the Sales Invoice."""
    # Apply as a negative additional discount
    doc.discount_amount_type = "Percentage"
    doc.additional_discount_percentage = percentage

    # Store the discount reason in the terms
    discount_note = _(
        "Sibling discount ({0}%) applied - Guardian: {1}"
    ).format(percentage, guardian)

    if not doc.terms:
        doc.terms = discount_note
    else:
        doc.terms += f"\n{discount_note}"
