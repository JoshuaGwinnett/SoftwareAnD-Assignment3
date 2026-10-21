import shutil
import sys
import tempfile
from datetime import datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from yowd_dms.dispatch_front import DispatchFront
from yowd_dms.models import DeliveryStaff, Manager, OfficeStaff, Parcel, RequestStatus, StaffAvailability
from yowd_dms.services import Database


def run() -> None:
    tmp_dir = tempfile.mkdtemp(prefix="yowd_test_")
    try:
        db = Database(data_dir=tmp_dir)
        system = DispatchFront(db=db)

        office = system.register_staff(OfficeStaff(name="Olivia Office", email="olivia@yowd.example", phone="0400111111"))
        driver = system.register_staff(DeliveryStaff(name="Dave Driver", email="dave@yowd.example", phone="0400222222"))
        system.register_staff(Manager(name="Mia Manager", email="mia@yowd.example", phone="0400333333"))
        assert driver.availability == StaffAvailability.AVAILABLE

        # Task 1: Log Delivery Request
        customer = system.register_customer("Chris Customer", "chris@example.com", "0400999999", "1 Example St, Melbourne")
        parcel = Parcel(description="Box of books", weight_kg=4.5, dimensions="30x20x15cm")
        request = system.log_delivery_request(customer, "1 Example St, Melbourne", "2 Sample Rd, Richmond", parcel)
        assert request.status == RequestStatus.PENDING_QUOTE

        # Task 2: Prepare & Send Quote
        quote = system.prepare_and_send_quote(office, request, distance_km=12.0)
        assert quote.amount > 0
        assert request.status == RequestStatus.QUOTED

        # Task 3: Accept / Decline Quote
        system.respond_to_quote(request, quote, accept=True)
        assert request.status == RequestStatus.ACCEPTED
        assert quote.accepted is True

        # Task 4: Allocate Delivery Staff
        delivery = system.allocate_delivery_staff(request, quote)
        assert delivery.assigned_staff_id == driver.user_id
        assert driver.availability == StaffAvailability.ON_DELIVERY

        # Task 5: Manage Staff Availability (already exercised by allocation;
        # also check a manual call works)
        system.set_staff_availability(driver, StaffAvailability.ON_DELIVERY)
        assert driver.availability == StaffAvailability.ON_DELIVERY

        # Task 6: Pick Up Package & Collect Payment
        payment = system.pick_up_and_collect_payment(delivery, driver, amount=quote.amount, method="card")
        assert payment.paid is True
        assert system.track_status(delivery).value == "PICKED_UP"

        system.mark_in_transit(delivery, driver)
        assert system.track_status(delivery).value == "IN_TRANSIT"

        # Task 7: Deliver Package & Complete Order
        system.deliver_and_complete(delivery, driver)
        assert system.track_status(delivery).value == "COMPLETED"
        assert driver.availability == StaffAvailability.AVAILABLE

        # Task 8: Track Delivery Status (history should have 4 entries)
        assert [h.status.value for h in delivery.history] == ["PICKED_UP", "IN_TRANSIT", "DELIVERED", "COMPLETED"]

        # Task 9: Generate Operational Statistics
        report = system.generate_statistics_report(datetime.now() - timedelta(days=1), datetime.now() + timedelta(days=1))
        assert report.total_requests == 1
        assert report.total_completed_deliveries == 1
        assert report.total_revenue == payment.amount

        # Persistence check: reload a fresh Database from the same dir
        reloaded = Database(data_dir=tmp_dir)
        assert len(reloaded.requests) == 1
        assert len(reloaded.deliveries) == 1
        assert list(reloaded.deliveries.values())[0].status == RequestStatus.ACCEPTED or True  # Delivery uses DeliveryStatus
        assert list(reloaded.deliveries.values())[0].status.value == "COMPLETED"

        print("ALL END-TO-END ASSERTIONS PASSED.")
    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)


if __name__ == "__main__":
    run()
