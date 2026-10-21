"""The four controllers from the Assignment 2 design.

Each controller owns one business-operation area and is invoked only
through the DispatchFront facade (dispatch_front.py), never directly
by the UI -- matching the Facade pattern in the finalised A2 design.
"""
from __future__ import annotations

from datetime import datetime
from typing import List, Optional

from .models import (
    Customer,
    Delivery,
    DeliveryRequest,
    DeliveryStaff,
    DeliveryStatus,
    OfficeStaff,
    Parcel,
    Payment,
    Quote,
    RequestStatus,
    StaffAvailability,
    StatisticsReport,
)
from .patterns import PricingStrategy, StatusObserver
from .services import Database, NotificationService


class RequestController:
    """Covers: Log Delivery Request, Prepare & Send Quote, Accept/Decline Quote."""

    def __init__(self, db: Database, notifier: NotificationService, pricing_strategy: PricingStrategy):
        self.db = db
        self.notifier = notifier
        self.pricing_strategy = pricing_strategy

    def log_delivery_request(
        self, customer: Customer, pickup_address: str, dropoff_address: str, parcel: Parcel
    ) -> DeliveryRequest:
        request = DeliveryRequest(
            customer_id=customer.user_id,
            pickup_address=pickup_address,
            dropoff_address=dropoff_address,
            parcel=parcel,
        )
        self.db.add_request(request)
        self.notifier.notify(customer.user_id, f"Your delivery request {request.request_id} has been logged.")
        return request

    def prepare_and_send_quote(
        self, office_staff: OfficeStaff, request: DeliveryRequest, distance_km: float
    ) -> Quote:
        amount = self.pricing_strategy.calculate_price(request.parcel, distance_km)
        quote = office_staff.prepare_quote(request, amount)
        self.db.add_quote(quote)
        request.update_status(RequestStatus.QUOTED)
        self.db.save_requests()
        self.notifier.notify(request.customer_id, f"A quote of ${amount:.2f} is ready for request {request.request_id}.")
        return quote

    def respond_to_quote(self, request: DeliveryRequest, quote: Quote, accept: bool) -> Quote:
        if quote.request_id != request.request_id:
            raise ValueError("Quote does not belong to this request.")
        if accept:
            quote.accept()
            request.update_status(RequestStatus.ACCEPTED)
        else:
            quote.decline()
            request.update_status(RequestStatus.DECLINED)
        self.db.save_quotes()
        self.db.save_requests()
        return quote


class AllocationController:
    """Covers: Allocate Delivery Staff, Manage Staff Availability."""

    def __init__(self, db: Database, notifier: NotificationService):
        self.db = db
        self.notifier = notifier

    def allocate_delivery_staff(self, request: DeliveryRequest, quote: Quote) -> Delivery:
        if quote.accepted is not True:
            raise ValueError("Cannot allocate staff before the quote is accepted.")
        available = self.db.available_delivery_staff()
        if not available:
            raise RuntimeError("No delivery staff currently available.")
        chosen: DeliveryStaff = available[0]

        delivery = Delivery(request_id=request.request_id, quote_id=quote.quote_id)
        delivery.assign_staff(chosen.user_id)
        self.db.add_delivery(delivery)

        self.set_staff_availability(chosen, StaffAvailability.ON_DELIVERY)
        self.notifier.notify(chosen.user_id, f"You have been allocated delivery {delivery.delivery_id}.")
        self.notifier.notify(request.customer_id, f"Delivery staff assigned for request {request.request_id}.")
        return delivery

    def set_staff_availability(self, staff: DeliveryStaff, status: StaffAvailability) -> None:
        staff.set_availability(status)
        self.db.save_staff()


class DeliveryController:
    """Covers: Pick Up Package & Collect Payment, Deliver Package & Complete Order, Track Delivery Status."""

    def __init__(self, db: Database, notifier: NotificationService, observers: Optional[List[StatusObserver]] = None):
        self.db = db
        self.notifier = notifier
        self.observers: List[StatusObserver] = observers or [notifier]

    def _publish_status(self, delivery: Delivery, status: DeliveryStatus, note: str, staff_id: str) -> None:
        delivery.add_status(status, note, staff_id)
        self.db.save_deliveries()
        for obs in self.observers:
            obs.on_status_changed(delivery, status)

    def pick_up_and_collect_payment(
        self, delivery: Delivery, delivery_staff: DeliveryStaff, amount: float, method: str
    ) -> Payment:
        payment = Payment(amount=amount, method=method, delivery_id=delivery.delivery_id)
        payment.process()
        delivery.payment = payment
        self._publish_status(delivery, DeliveryStatus.PICKED_UP, "Package collected from pickup address.", delivery_staff.user_id)
        return payment

    def mark_in_transit(self, delivery: Delivery, delivery_staff: DeliveryStaff) -> None:
        self._publish_status(delivery, DeliveryStatus.IN_TRANSIT, "Package is on the way.", delivery_staff.user_id)

    def deliver_and_complete(self, delivery: Delivery, delivery_staff: DeliveryStaff, allocation_controller: AllocationController) -> None:
        self._publish_status(delivery, DeliveryStatus.DELIVERED, "Package delivered to dropoff address.", delivery_staff.user_id)
        self._publish_status(delivery, DeliveryStatus.COMPLETED, "Order completed.", delivery_staff.user_id)
        allocation_controller.set_staff_availability(delivery_staff, StaffAvailability.AVAILABLE)
        self.notifier.notify(delivery.request_id, f"Delivery {delivery.delivery_id} is complete.")

    def track_status(self, delivery: Delivery) -> DeliveryStatus:
        return delivery.current_status()


class ReportingController:
    """Covers: Generate Operational Statistics."""

    def __init__(self, db: Database):
        self.db = db

    def generate_statistics_report(self, period_start: datetime, period_end: datetime) -> StatisticsReport:
        requests_in_period = [
            r for r in self.db.requests.values()
            if period_start <= datetime.fromisoformat(r.created_at) <= period_end
        ]
        completed = [d for d in self.db.deliveries.values() if d.status == DeliveryStatus.COMPLETED]
        total_revenue = sum(d.payment.amount for d in completed if d.payment)

        delivery_times = []
        for d in completed:
            if len(d.history) >= 1:
                start = datetime.fromisoformat(d.history[0].timestamp)
                end = datetime.fromisoformat(d.history[-1].timestamp)
                delivery_times.append((end - start).total_seconds() / 3600)
        avg_hours = round(sum(delivery_times) / len(delivery_times), 2) if delivery_times else 0.0

        return StatisticsReport(
            period_start=period_start.isoformat(timespec="seconds"),
            period_end=period_end.isoformat(timespec="seconds"),
            total_requests=len(requests_in_period),
            total_completed_deliveries=len(completed),
            total_revenue=round(total_revenue, 2),
            average_delivery_time_hours=avg_hours,
        )
