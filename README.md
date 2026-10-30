# YOWD Delivery Management System — Implementation

Python 3 implementation of the "Your Order, We Deliver" (YOWD) Delivery
Management System, built directly from the group's finalised Assignment 2
Object Design.

## Platform
 
- Developed & tested in a GitHub Codespace (Ubuntu Linux)
- Python3.14.2 , standard library only (no third-party packages)
- Editor: Visual Studio Code (web)

## Running it

```
cd yowd_dms
python3 -m yowd_dms.main
```

On first run the system bootstraps one Office Staff, one Delivery Staff and
one Manager so every menu option is immediately usable. All data is persisted
as JSON files under `./data` (file-based persistence, used in place of a real
DBMS per the Assignment 1 requirements) and is reloaded automatically next
time the program starts.

## Running the automated test

```
cd yowd_dms
python3 tests/test_end_to_end.py
```

This drives `DispatchFront` through all 9 business operation areas in one
pass (log request → quote → accept → allocate → pick up/pay → in transit →
deliver/complete → track → statistics report) and asserts the expected state
at each step, including that data reloads correctly from disk afterwards.

## Project layout

```
yowd_dms/
  __init__.py
  models.py          Domain classes: User/Customer/Staff hierarchy,
                      DeliveryRequest, Parcel, Quote, Delivery, Payment,
                      StatusEntry, StatisticsReport
  patterns.py         StatusObserver + PricingStrategy interfaces,
                      StandardPricingStrategy (Observer & Strategy patterns)
  services.py         Database (file-based persistence) and
                      NotificationService (concrete StatusObserver)
  controllers.py      RequestController, AllocationController,
                      DeliveryController, ReportingController
  dispatch_front.py   DispatchFront — the Facade the UI calls
  validation.py       Input-validation helpers for the textual UI
  main.py             Textual menu-driven UI / bootstrap process
tests/
  test_end_to_end.py  Scripted end-to-end test across all 9 task areas
data/                 JSON data files (file-based persistence), created at
                      runtime — empty in this submission
```

## Mapping to the Assignment 1 business operation areas

All 9 task areas are fully implemented and wired together as one pipeline
(they depend on each other in sequence, so implementing a subset in isolation
wasn't practical):

1. Log Delivery Request — `RequestController.log_delivery_request`
2. Prepare & Send Quote — `RequestController.prepare_and_send_quote`
3. Accept / Decline Quote — `RequestController.respond_to_quote`
4. Allocate Delivery Staff — `AllocationController.allocate_delivery_staff`
5. Manage Staff Availability — `AllocationController.set_staff_availability`
6. Pick Up Package & Collect Payment — `DeliveryController.pick_up_and_collect_payment`
7. Deliver Package & Complete Order — `DeliveryController.deliver_and_complete`
8. Track Delivery Status — `DeliveryController.track_status`
9. Generate Operational Statistics — `ReportingController.generate_statistics_report`

Payment-gateway processing is intentionally out of scope (per the
Assignment 1 requirement) — `Payment.process()` simply records that payment
was collected.
