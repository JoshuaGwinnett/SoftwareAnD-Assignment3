"""Design-pattern interfaces used by the system.

- StatusObserver / Observer pattern: lets interested parties (e.g. the
  notification service) react whenever a Delivery's status changes,
  without the Delivery or controllers needing to know who's listening.
- PricingStrategy / Strategy pattern: lets the quote-pricing algorithm
  vary (standard pricing now, express/discount pricing later) without
  changing OfficeStaff or RequestController.
"""
from __future__ import annotations

from abc import ABC, abstractmethod

from .models import Delivery, DeliveryStatus, Parcel


class StatusObserver(ABC):
    """Observer interface notified whenever a delivery's status changes."""

    @abstractmethod
    def on_status_changed(self, delivery: Delivery, status: DeliveryStatus) -> None:
        raise NotImplementedError


class PricingStrategy(ABC):
    """Strategy interface for computing a delivery quote amount."""

    @abstractmethod
    def calculate_price(self, parcel: Parcel, distance_km: float) -> float:
        raise NotImplementedError


class StandardPricingStrategy(PricingStrategy):
    """Default flat-rate-plus-weight-plus-distance pricing model."""

    BASE_FEE = 5.00
    PER_KG = 1.20
    PER_KM = 0.80

    def calculate_price(self, parcel: Parcel, distance_km: float) -> float:
        price = self.BASE_FEE + (parcel.weight_kg * self.PER_KG) + (distance_km * self.PER_KM)
        return round(price, 2)
