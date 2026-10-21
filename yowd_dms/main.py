"""Textual UI entry point for the YOWD Delivery Management System.

A simple menu-driven console UI sitting on top of DispatchFront, the
single facade through which every business operation is invoked.
Run with:  python -m yowd_dms.main
"""
from __future__ import annotations

from datetime import datetime, timedelta

from .dispatch_front import DispatchFront
from .models import DeliveryStaff, Manager, OfficeStaff, Parcel, StaffAvailability
from .validation import prompt_choice, prompt_float, prompt_nonblank, prompt_yes_no


def bootstrap(system: DispatchFront) -> None:
    """Seed a minimal set of staff on first run (bootstrap process).

    Mirrors the "system bootstrap" step described in the Assignment 2
    design: on startup, the system loads persisted data (handled by
    Database.__init__) and ensures at least one staff member of each
    required role exists so the demo flows are runnable immediately.
    """
    if not system.list_office_staff():
        system.register_staff(OfficeStaff(name="Olivia Office", email="olivia@yowd.example", phone="0400111111"))
    if not system.list_delivery_staff():
        system.register_staff(DeliveryStaff(name="Dave Driver", email="dave@yowd.example", phone="0400222222"))
    if not system.list_managers():
        system.register_staff(Manager(name="Mia Manager", email="mia@yowd.example", phone="0400333333"))


MENU = """
==================== YOWD Delivery Management System ====================
 1. Register customer
 2. Log a delivery request
 3. Prepare & send a quote                (Office Staff)
 4. Accept / decline a quote               (Customer)
 5. Allocate delivery staff                (Office Staff)
 6. Set staff availability                 (Delivery Staff)
 7. Pick up package & collect payment      (Delivery Staff)
 8. Mark delivery in transit               (Delivery Staff)
 9. Deliver package & complete order       (Delivery Staff)
10. Track delivery status                  (Anyone)
11. Generate operational statistics report (Manager)
12. List all requests / deliveries
 0. Exit
===========================================================================
"""


def choose_from(label: str, items: list, display) -> object:
    if not items:
        print(f"  -> No {label} available yet.")
        return None
    for i, item in enumerate(items, start=1):
        print(f"  {i}. {display(item)}")
    while True:
        raw = input(f"Select {label} (number): ").strip()
        if raw.isdigit() and 1 <= int(raw) <= len(items):
            return items[int(raw) - 1]
        print("  -> Invalid selection, try again.")


def action_register_customer(system: DispatchFront) -> None:
    name = prompt_nonblank("Customer name")
    email = prompt_nonblank("Email")
    phone = prompt_nonblank("Phone")
    address = prompt_nonblank("Address")
    customer = system.register_customer(name, email, phone, address)
    print(f"  -> Registered customer {customer.user_id} ({customer.name}).")


def action_log_request(system: DispatchFront) -> None:
    customer = choose_from("customer", list(system.db.customers.values()), lambda c: f"{c.user_id} - {c.name}")
    if not customer:
        return
    pickup = prompt_nonblank("Pickup address")
    dropoff = prompt_nonblank("Dropoff address")
    description = prompt_nonblank("Parcel description")
    weight = prompt_float("Parcel weight (kg)", min_value=0.1)
    dimensions = prompt_nonblank("Parcel dimensions (e.g. 30x20x15cm)")
    parcel = Parcel(description=description, weight_kg=weight, dimensions=dimensions)
    request = system.log_delivery_request(customer, pickup, dropoff, parcel)
    print(f"  -> Logged request {request.request_id}, status={request.status.value}.")


def action_prepare_quote(system: DispatchFront) -> None:
    staff = choose_from("office staff member", system.list_office_staff(), lambda s: f"{s.user_id} - {s.name}")
    if not staff:
        return
    request = choose_from(
        "delivery request", system.list_requests(),
        lambda r: f"{r.request_id} - {r.pickup_address} -> {r.dropoff_address} ({r.status.value})",
    )
    if not request:
        return
    distance_km = prompt_float("Estimated distance (km)", min_value=0.1)
    quote = system.prepare_and_send_quote(staff, request, distance_km)
    print(f"  -> Quote {quote.quote_id} prepared: ${quote.amount:.2f}.")


def action_respond_to_quote(system: DispatchFront) -> None:
    request = choose_from(
        "delivery request", [r for r in system.list_requests() if system.quotes_for_request(r.request_id)],
        lambda r: f"{r.request_id} ({r.status.value})",
    )
    if not request:
        return
    quote = choose_from(
        "quote", system.quotes_for_request(request.request_id),
        lambda q: f"{q.quote_id} - ${q.amount:.2f} (accepted={q.accepted})",
    )
    if not quote:
        return
    accept = prompt_yes_no("Accept this quote?")
    system.respond_to_quote(request, quote, accept)
    print(f"  -> Quote {'accepted' if accept else 'declined'}. Request status: {request.status.value}.")


def action_allocate_staff(system: DispatchFront) -> None:
    from .models import RequestStatus
    accepted_requests = [r for r in system.list_requests() if r.status == RequestStatus.ACCEPTED]
    request = choose_from("accepted request", accepted_requests, lambda r: f"{r.request_id} ({r.status.value})")
    if not request:
        return
    accepted_quotes = [q for q in system.quotes_for_request(request.request_id) if q.accepted]
    quote = choose_from("accepted quote", accepted_quotes, lambda q: f"{q.quote_id} - ${q.amount:.2f}")
    if not quote:
        return
    try:
        delivery = system.allocate_delivery_staff(request, quote)
    except RuntimeError as exc:
        print(f"  -> {exc}")
        return
    print(f"  -> Delivery {delivery.delivery_id} created, assigned staff {delivery.assigned_staff_id}.")


def action_set_availability(system: DispatchFront) -> None:
    staff = choose_from("delivery staff member", system.list_delivery_staff(), lambda s: f"{s.user_id} - {s.name} ({s.availability.value})")
    if not staff:
        return
    status_str = prompt_choice("New availability", [s.value for s in StaffAvailability])
    system.set_staff_availability(staff, StaffAvailability(status_str))
    print(f"  -> {staff.name} is now {staff.availability.value}.")


def _choose_delivery(system: DispatchFront):
    return choose_from("delivery", system.list_deliveries(), lambda d: f"{d.delivery_id} ({d.status.value})")


def action_pick_up(system: DispatchFront) -> None:
    delivery = _choose_delivery(system)
    if not delivery:
        return
    staff = system.get_staff(delivery.assigned_staff_id)
    amount = prompt_float("Payment amount collected ($)", min_value=0.01)
    method = prompt_choice("Payment method", ["cash", "card"])
    payment = system.pick_up_and_collect_payment(delivery, staff, amount, method)
    print(f"  -> Payment {payment.payment_id} recorded (${payment.amount:.2f}, {payment.method}).")


def action_in_transit(system: DispatchFront) -> None:
    delivery = _choose_delivery(system)
    if not delivery:
        return
    staff = system.get_staff(delivery.assigned_staff_id)
    system.mark_in_transit(delivery, staff)
    print(f"  -> Delivery {delivery.delivery_id} marked IN_TRANSIT.")


def action_deliver_complete(system: DispatchFront) -> None:
    delivery = _choose_delivery(system)
    if not delivery:
        return
    staff = system.get_staff(delivery.assigned_staff_id)
    system.deliver_and_complete(delivery, staff)
    print(f"  -> Delivery {delivery.delivery_id} marked COMPLETED.")


def action_track_status(system: DispatchFront) -> None:
    delivery = _choose_delivery(system)
    if not delivery:
        return
    status = system.track_status(delivery)
    print(f"  -> Delivery {delivery.delivery_id} current status: {status.value}")
    for entry in delivery.history:
        print(f"       {entry.timestamp}  {entry.status.value}  ({entry.note})")


def action_generate_report(system: DispatchFront) -> None:
    days_str = input("Report over how many past days? [30]: ").strip()
    days = int(days_str) if days_str.isdigit() else 30
    end = datetime.now()
    start = end - timedelta(days=days)
    report = system.generate_statistics_report(start, end)
    print(f"  -> Report {report.report_id} ({report.period_start} to {report.period_end}):")
    print(f"       Total requests logged     : {report.total_requests}")
    print(f"       Total completed deliveries: {report.total_completed_deliveries}")
    print(f"       Total revenue             : ${report.total_revenue:.2f}")
    print(f"       Avg delivery time (hours) : {report.average_delivery_time_hours}")


def action_list_all(system: DispatchFront) -> None:
    print("\n-- Delivery Requests --")
    for r in system.list_requests():
        print(f"  {r.request_id}: {r.pickup_address} -> {r.dropoff_address} | {r.status.value}")
    print("\n-- Deliveries --")
    for d in system.list_deliveries():
        print(f"  {d.delivery_id}: request={d.request_id} staff={d.assigned_staff_id} | {d.status.value}")


ACTIONS = {
    "1": action_register_customer,
    "2": action_log_request,
    "3": action_prepare_quote,
    "4": action_respond_to_quote,
    "5": action_allocate_staff,
    "6": action_set_availability,
    "7": action_pick_up,
    "8": action_in_transit,
    "9": action_deliver_complete,
    "10": action_track_status,
    "11": action_generate_report,
    "12": action_list_all,
}


def main() -> None:
    system = DispatchFront()
    bootstrap(system)
    print("YOWD Delivery Management System started. Data persisted under ./data")
    while True:
        print(MENU)
        choice = input("Select an option: ").strip()
        if choice == "0":
            print("Goodbye.")
            break
        action = ACTIONS.get(choice)
        if not action:
            print("  -> Invalid option.")
            continue
        try:
            action(system)
        except Exception as exc:  # keep the UI alive on any business-rule error
            print(f"  -> Error: {exc}")


if __name__ == "__main__":
    main()
