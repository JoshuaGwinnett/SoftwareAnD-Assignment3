"""Domain model classes for the YOWD Delivery Management System.

Mirrors the class design from the finalised Assignment 2 Object
Design Document: the User/Staff/Customer hierarchy, the
DeliveryRequest -> Quote -> Delivery entity chain, and the simple
data-holder classes (Payment, StatusEntry, StatisticsReport).
"""
from __future__ import annotations

import itertools
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional


# ---------------------------------------------------------------------------
# Shared id generator (stand-in for DB auto-increment keys)
# ---------------------------------------------------------------------------
_id_counter = itertools.count(1)


def next_id(prefix: str) -> str:
    return f"{prefix}{next(_id_counter):04d}"


# ---------------------------------------------------------------------------
# Enumerations
# ---------------------------------------------------------------------------
class RequestStatus(str, Enum):
    PENDING_QUOTE = "PENDING_QUOTE"
    QUOTED = "QUOTED"
    ACCEPTED = "ACCEPTED"
    DECLINED = "DECLINED"


class DeliveryStatus(str, Enum):
    AWAITING_ALLOCATION = "AWAITING_ALLOCATION"
    ALLOCATED = "ALLOCATED"
    PICKED_UP = "PICKED_UP"
    IN_TRANSIT = "IN_TRANSIT"
    DELIVERED = "DELIVERED"
    COMPLETED = "COMPLETED"


class StaffAvailability(str, Enum):
    AVAILABLE = "AVAILABLE"
    UNAVAILABLE = "UNAVAILABLE"
    ON_DELIVERY = "ON_DELIVERY"


# ---------------------------------------------------------------------------
# User hierarchy
# ---------------------------------------------------------------------------
@dataclass
class User:
    name: str
    email: str
    phone: str
    user_id: str = field(default_factory=lambda: next_id("U"))

    def get_profile(self) -> dict:
        return {
            "user_id": self.user_id,
            "name": self.name,
            "email": self.email,
            "phone": self.phone,
            "role": self.__class__.__name__,
        }


@dataclass
class Customer(User):
    address: str = ""

    def to_dict(self) -> dict:
        d = self.get_profile()
        d["address"] = self.address
        return d


@dataclass
class Staff(User):
    availability: StaffAvailability = StaffAvailability.AVAILABLE

    def set_availability(self, status: StaffAvailability) -> None:
        self.availability = status

    def to_dict(self) -> dict:
        d = self.get_profile()
        d["availability"] = self.availability.value
        return d


@dataclass
class OfficeStaff(Staff):
    def prepare_quote(self, request: "DeliveryRequest", amount: float) -> "Quote":
        return Quote(request_id=request.request_id, amount=amount, prepared_by=self.user_id)


@dataclass
class DeliveryStaff(Staff):
    def record_status(self, delivery: "Delivery", status: DeliveryStatus, note: str = "") -> "StatusEntry":
        return delivery.add_status(status, note, staff_id=self.user_id)


@dataclass
class Manager(Staff):
    def request_report(self, reporting_controller, period_start: datetime, period_end: datetime) -> "StatisticsReport":
        return reporting_controller.generate_statistics_report(period_start, period_end)


# ---------------------------------------------------------------------------
# Parcel / DeliveryRequest / Quote / Delivery
# ---------------------------------------------------------------------------
@dataclass
class Parcel:
    description: str
    weight_kg: float
    dimensions: str
    parcel_id: str = field(default_factory=lambda: next_id("P"))

    def to_dict(self) -> dict:
        return {
            "parcel_id": self.parcel_id,
            "description": self.description,
            "weight_kg": self.weight_kg,
            "dimensions": self.dimensions,
        }


@dataclass
class DeliveryRequest:
    customer_id: str
    pickup_address: str
    dropoff_address: str
    parcel: Parcel
    status: RequestStatus = RequestStatus.PENDING_QUOTE
    request_id: str = field(default_factory=lambda: next_id("R"))
    created_at: str = field(default_factory=lambda: datetime.now().isoformat(timespec="seconds"))

    def update_status(self, status: RequestStatus) -> None:
        self.status = status

    def to_dict(self) -> dict:
        return {
            "request_id": self.request_id,
            "customer_id": self.customer_id,
            "pickup_address": self.pickup_address,
            "dropoff_address": self.dropoff_address,
            "parcel": self.parcel.to_dict(),
            "status": self.status.value,
            "created_at": self.created_at,
        }

    @staticmethod
    def from_dict(d: dict) -> "DeliveryRequest":
        parcel = Parcel(**d["parcel"])
        req = DeliveryRequest(
            customer_id=d["customer_id"],
            pickup_address=d["pickup_address"],
            dropoff_address=d["dropoff_address"],
            parcel=parcel,
            status=RequestStatus(d["status"]),
            request_id=d["request_id"],
            created_at=d["created_at"],
        )
        return req


@dataclass
class Quote:
    request_id: str
    amount: float
    prepared_by: str
    quote_id: str = field(default_factory=lambda: next_id("Q"))
    accepted: Optional[bool] = None

    def accept(self) -> None:
        self.accepted = True

    def decline(self) -> None:
        self.accepted = False

    def to_dict(self) -> dict:
        return {
            "quote_id": self.quote_id,
            "request_id": self.request_id,
            "amount": self.amount,
            "prepared_by": self.prepared_by,
            "accepted": self.accepted,
        }

    @staticmethod
    def from_dict(d: dict) -> "Quote":
        return Quote(
            request_id=d["request_id"],
            amount=d["amount"],
            prepared_by=d["prepared_by"],
            quote_id=d["quote_id"],
            accepted=d["accepted"],
        )


@dataclass
class StatusEntry:
    status: DeliveryStatus
    note: str
    staff_id: str
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat(timespec="seconds"))

    def to_dict(self) -> dict:
        return {
            "status": self.status.value,
            "note": self.note,
            "staff_id": self.staff_id,
            "timestamp": self.timestamp,
        }

    @staticmethod
    def from_dict(d: dict) -> "StatusEntry":
        return StatusEntry(
            status=DeliveryStatus(d["status"]),
            note=d["note"],
            staff_id=d["staff_id"],
            timestamp=d["timestamp"],
        )


@dataclass
class Payment:
    amount: float
    method: str
    delivery_id: str
    paid: bool = False
    payment_id: str = field(default_factory=lambda: next_id("PAY"))

    def process(self) -> None:
        # Real payment gateway integration is out of scope for this
        # assignment (per the A1 requirements) -- this simply records
        # that a payment was collected on pickup.
        self.paid = True

    def to_dict(self) -> dict:
        return {
            "payment_id": self.payment_id,
            "amount": self.amount,
            "method": self.method,
            "delivery_id": self.delivery_id,
            "paid": self.paid,
        }

    @staticmethod
    def from_dict(d: dict) -> "Payment":
        return Payment(
            amount=d["amount"],
            method=d["method"],
            delivery_id=d["delivery_id"],
            paid=d["paid"],
            payment_id=d["payment_id"],
        )


@dataclass
class Delivery:
    request_id: str
    quote_id: str
    delivery_id: str = field(default_factory=lambda: next_id("D"))
    assigned_staff_id: Optional[str] = None
    status: DeliveryStatus = DeliveryStatus.AWAITING_ALLOCATION
    history: list = field(default_factory=list)  # list[StatusEntry]
    payment: Optional[Payment] = None

    def assign_staff(self, staff_id: str) -> None:
        self.assigned_staff_id = staff_id
        self.status = DeliveryStatus.ALLOCATED

    def add_status(self, status: DeliveryStatus, note: str, staff_id: str) -> StatusEntry:
        entry = StatusEntry(status=status, note=note, staff_id=staff_id)
        self.history.append(entry)
        self.status = status
        return entry

    def current_status(self) -> DeliveryStatus:
        return self.status

    def to_dict(self) -> dict:
        return {
            "delivery_id": self.delivery_id,
            "request_id": self.request_id,
            "quote_id": self.quote_id,
            "assigned_staff_id": self.assigned_staff_id,
            "status": self.status.value,
            "history": [h.to_dict() for h in self.history],
            "payment": self.payment.to_dict() if self.payment else None,
        }

    @staticmethod
    def from_dict(d: dict) -> "Delivery":
        dlv = Delivery(
            request_id=d["request_id"],
            quote_id=d["quote_id"],
            delivery_id=d["delivery_id"],
            assigned_staff_id=d["assigned_staff_id"],
            status=DeliveryStatus(d["status"]),
        )
        dlv.history = [StatusEntry.from_dict(h) for h in d["history"]]
        dlv.payment = Payment.from_dict(d["payment"]) if d["payment"] else None
        return dlv


@dataclass
class StatisticsReport:
    period_start: str
    period_end: str
    total_requests: int
    total_completed_deliveries: int
    total_revenue: float
    average_delivery_time_hours: float
    report_id: str = field(default_factory=lambda: next_id("REP"))

    def to_dict(self) -> dict:
        return self.__dict__.copy()
