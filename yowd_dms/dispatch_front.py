"""DispatchFront: the single Facade the UI talks to.

Wires up the Database, NotificationService and the four controllers,
and exposes one flat set of methods covering every business
operation area -- the UI never touches a controller directly, matching
the Facade pattern from the finalised Assignment 2 design.
"""
from __future__ import annotations

from datetime import datetime
from typing import List, Optional

from .controllers import (
    AllocationController,
    DeliveryController,
    ReportingController,
    RequestController,
)
from .models import (
    Customer,
    Delivery,
    DeliveryRequest,
    DeliveryStaff,
    Manager,
    OfficeStaff,
    Parcel,
    Payment,
    Quote,
    Staff,
    StatisticsReport,
)
from .patterns import PricingStrategy, StandardPricingStrategy
from .services import Database, NotificationService


class DispatchFront:
    def __init__(self, db: Optional[Database] = None, pricing_strategy: Optional[PricingStrategy] = None):
        self.db = db or Database()
        self.notifier = NotificationService()
        strategy = pricing_strategy or StandardPricingStrategy()

        self.request_controller = RequestController(self.db, self.notifier, strategy)
        self.allocation_controller = AllocationController(self.db, self.notifier)
        self.delivery_controller = DeliveryController(self.db, self.notifier)
        self.reporting_controller = ReportingController(self.db)

    # -- customer / staff registration --------------------------------------
    def register_customer(self, name: str, email: str, phone: str, address: str) -> Customer:
        customer = Customer(name=name, email=email, phone=phone, address=address)
        self.db.add_customer(customer)
        return customer

    def register_staff(self, staff: Staff) -> Staff:
        self.db.add_staff(staff)
        return staff

    # -- Task 1: Log Delivery Request ----------------------------------------
    def log_delivery_request(self, customer: Customer, pickup: str, dropoff: str, parcel: Parcel) -> DeliveryRequest:
        return self.request_controller.log_delivery_request(customer, pickup, dropoff, parcel)

    # -- Task 2: Prepare & Send Quote -----------------------------------------
    def prepare_and_send_quote(self, office_staff: OfficeStaff, request: DeliveryRequest, distance_km: float) -> Quote:
        return self.request_controller.prepare_and_send_quote(office_staff, request, distance_km)

    # -- Task 3: Accept / Decline Quote ---------------------------------------
    def respond_to_quote(self, request: DeliveryRequest, quote: Quote, accept: bool) -> Quote:
        return self.request_controller.respond_to_quote(request, quote, accept)

    # -- Task 4: Allocate Delivery Staff --------------------------------------
    def allocate_delivery_staff(self, request: DeliveryRequest, quote: Quote) -> Delivery:
        return self.allocation_controller.allocate_delivery_staff(request, quote)

    # -- Task 5: Manage Staff Availability -------------------------------------
    def set_staff_availability(self, staff: DeliveryStaff, status) -> None:
        self.allocation_controller.set_staff_availability(staff, status)

    # -- Task 6: Pick Up Package & Collect Payment -----------------------------
    def pick_up_and_collect_payment(self, delivery: Delivery, staff: DeliveryStaff, amount: float, method: str) -> Payment:
        return self.delivery_controller.pick_up_and_collect_payment(delivery, staff, amount, method)

    def mark_in_transit(self, delivery: Delivery, staff: DeliveryStaff) -> None:
        self.delivery_controller.mark_in_transit(delivery, staff)

    # -- Task 7: Deliver Package & Complete Order -------------------------------
    def deliver_and_complete(self, delivery: Delivery, staff: DeliveryStaff) -> None:
        self.delivery_controller.deliver_and_complete(delivery, staff, self.allocation_controller)

    # -- Task 8: Track Delivery Status -----------------------------------------
    def track_status(self, delivery: Delivery):
        return self.delivery_controller.track_status(delivery)

    # -- Task 9: Generate Operational Statistics --------------------------------
    def generate_statistics_report(self, period_start: datetime, period_end: datetime) -> StatisticsReport:
        return self.reporting_controller.generate_statistics_report(period_start, period_end)

    # -- lookup helpers (used by the UI) ---------------------------------------
    def get_customer(self, customer_id: str) -> Optional[Customer]:
        return self.db.customers.get(customer_id)

    def get_staff(self, staff_id: str) -> Optional[Staff]:
        return self.db.staff.get(staff_id)

    def list_office_staff(self) -> List[OfficeStaff]:
        return [s for s in self.db.staff.values() if isinstance(s, OfficeStaff)]

    def list_delivery_staff(self) -> List[DeliveryStaff]:
        return [s for s in self.db.staff.values() if isinstance(s, DeliveryStaff)]

    def list_managers(self) -> List[Manager]:
        return [s for s in self.db.staff.values() if isinstance(s, Manager)]

    def list_requests(self) -> List[DeliveryRequest]:
        return list(self.db.requests.values())

    def quotes_for_request(self, request_id: str) -> List[Quote]:
        return self.db.quotes_for_request(request_id)

    def delivery_for_request(self, request_id: str) -> Optional[Delivery]:
        return self.db.delivery_for_request(request_id)

    def list_deliveries(self) -> List[Delivery]:
        return list(self.db.deliveries.values())
