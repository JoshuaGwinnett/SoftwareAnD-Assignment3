"""Support services: file-based Database persistence and NotificationService.

Database substitutes for a real DBMS, per the Assignment 1 requirement
that file-based storage is an acceptable alternative to a database.
Each entity type is persisted as a JSON array in its own file under
./data, loaded into memory on startup and rewritten on every mutation.
"""
from __future__ import annotations

import json
import os
from typing import Dict, List, Optional

from .models import (
    Customer,
    Delivery,
    DeliveryRequest,
    DeliveryStaff,
    Manager,
    OfficeStaff,
    Payment,
    Quote,
    StatisticsReport,
    Staff,
    StaffAvailability,
    User,
)
from .patterns import StatusObserver


DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")


class Database:
    """Simple file-backed persistence layer (JSON-per-entity-type).

    Acts as the single source of truth the controllers read from and
    write through, matching the Dispatcher -> Database "persists via"
    dependency in the Assignment 2 class diagram.
    """

    def __init__(self, data_dir: str = DATA_DIR):
        self.data_dir = data_dir
        os.makedirs(self.data_dir, exist_ok=True)
        self.customers: Dict[str, Customer] = {}
        self.staff: Dict[str, Staff] = {}
        self.requests: Dict[str, DeliveryRequest] = {}
        self.quotes: Dict[str, Quote] = {}
        self.deliveries: Dict[str, Delivery] = {}
        self._load_all()

    # -- file helpers -----------------------------------------------------
    def _path(self, name: str) -> str:
        return os.path.join(self.data_dir, f"{name}.json")

    def _read_json(self, name: str) -> list:
        path = self._path(name)
        if not os.path.exists(path):
            return []
        with open(path, "r", encoding="utf-8") as f:
            content = f.read().strip()
            return json.loads(content) if content else []

    def _write_json(self, name: str, records: list) -> None:
        with open(self._path(name), "w", encoding="utf-8") as f:
            json.dump(records, f, indent=2)

    # -- loading ------------------------------------------------------------
    def _load_all(self) -> None:
        for d in self._read_json("customers"):
            c = Customer(name=d["name"], email=d["email"], phone=d["phone"], address=d["address"])
            c.user_id = d["user_id"]
            self.customers[c.user_id] = c

        for d in self._read_json("staff"):
            role = d.get("role")
            cls = {"OfficeStaff": OfficeStaff, "DeliveryStaff": DeliveryStaff, "Manager": Manager}.get(role, Staff)
            s = cls(name=d["name"], email=d["email"], phone=d["phone"])
            s.user_id = d["user_id"]
            s.availability = StaffAvailability(d["availability"])
            self.staff[s.user_id] = s

        for d in self._read_json("requests"):
            r = DeliveryRequest.from_dict(d)
            self.requests[r.request_id] = r

        for d in self._read_json("quotes"):
            q = Quote.from_dict(d)
            self.quotes[q.quote_id] = q

        for d in self._read_json("deliveries"):
            dl = Delivery.from_dict(d)
            self.deliveries[dl.delivery_id] = dl

    # -- persistence (save-through on every mutating call) ------------------
    def save_customers(self) -> None:
        self._write_json("customers", [c.to_dict() for c in self.customers.values()])

    def save_staff(self) -> None:
        self._write_json("staff", [s.to_dict() for s in self.staff.values()])

    def save_requests(self) -> None:
        self._write_json("requests", [r.to_dict() for r in self.requests.values()])

    def save_quotes(self) -> None:
        self._write_json("quotes", [q.to_dict() for q in self.quotes.values()])

    def save_deliveries(self) -> None:
        self._write_json("deliveries", [d.to_dict() for d in self.deliveries.values()])

    # -- CRUD-ish helpers used by the controllers ----------------------------
    def add_customer(self, customer: Customer) -> None:
        self.customers[customer.user_id] = customer
        self.save_customers()

    def find_customer_by_email(self, email: str) -> Optional[Customer]:
        return next((c for c in self.customers.values() if c.email == email), None)

    def add_staff(self, staff: Staff) -> None:
        self.staff[staff.user_id] = staff
        self.save_staff()

    def available_delivery_staff(self) -> List[DeliveryStaff]:
        return [
            s for s in self.staff.values()
            if isinstance(s, DeliveryStaff) and s.availability == StaffAvailability.AVAILABLE
        ]

    def add_request(self, request: DeliveryRequest) -> None:
        self.requests[request.request_id] = request
        self.save_requests()

    def add_quote(self, quote: Quote) -> None:
        self.quotes[quote.quote_id] = quote
        self.save_quotes()

    def add_delivery(self, delivery: Delivery) -> None:
        self.deliveries[delivery.delivery_id] = delivery
        self.save_deliveries()

    def quotes_for_request(self, request_id: str) -> List[Quote]:
        return [q for q in self.quotes.values() if q.request_id == request_id]

    def delivery_for_request(self, request_id: str) -> Optional[Delivery]:
        return next((d for d in self.deliveries.values() if d.request_id == request_id), None)


class NotificationService(StatusObserver):
    """Concrete StatusObserver: logs/prints customer + staff notifications.

    Stands in for a real SMS/email gateway, which is out of scope per
    the Assignment 1 requirement that no real external payment/notification
    integration is required -- notifications are simply displayed/logged.
    """

    def __init__(self, log_path: Optional[str] = None):
        self.log_path = log_path or os.path.join(DATA_DIR, "notifications.log")
        os.makedirs(os.path.dirname(self.log_path), exist_ok=True)

    def on_status_changed(self, delivery: Delivery, status) -> None:
        message = f"[NOTIFY] Delivery {delivery.delivery_id} status changed to {status.value}"
        self._emit(message)

    def notify(self, recipient_user_id: str, message: str) -> None:
        self._emit(f"[NOTIFY -> {recipient_user_id}] {message}")

    def _emit(self, message: str) -> None:
        print(message)
        with open(self.log_path, "a", encoding="utf-8") as f:
            f.write(message + "\n")
