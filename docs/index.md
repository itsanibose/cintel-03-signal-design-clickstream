# Signal Design for Clickstream Analysis

Continuous Intelligence | Project 03 | Clickstream Analysis

## Overview

A high-performance analytics pipeline built with Polars
to engineer behavioral telemetry metrics—tracking like
 session durations,browsing velocity, cart friction ratios,
and user inactivity thresholds—from raw online shopping
event streams.

## Data

The example uses system metrics from `data/2020-Jan.csv`.

### Data Schema & Engineered Metrics

Each row in the raw dataset contains the following baseline fields:

* `event_time`   – The timestamp of the interaction (stored as UTC).
* `event_type`   – The type of user action (`view`, `cart`, `remove_from_cart`, `purchase`).
* `price`        – The cost of the product at the time of the event.
* `user_session` – A unique string ID tracking a single browser session.

[View Example Dataset](https://github.com/itsanibose/cintel-03-signal-design-clickstream/blob/main/data/example-data.csv)

## Methods

The pipeline creates three monitoring signals.

From the above raw events, the Polars pipeline aggregates and calculates:

* `user_session`        - User's session id
* `session_start_time`  - Session start time
* `session_end_time`    - Session end  time
* `session_duration`    - Session duration
* `total_events`        - Total number of events
* `views`               - Number of View events
* `carts`               - Number of cart events
* `remove_from_carts`   - Number of times removed from cart
* `purchases`           - Total number of purchase
* `cart_to_view_ratio`  - Cart to View ration
* `purchase_to_cart_ratio` - Purchase to cart ratio
* `session_conversion_rate`- Overall conversion rate
* `abandoned_cart`         - Abondoned cart


## Results

The example signals reveal:

| Signal | Observed Range |
|---|---|
| Error rate | 0% to 2.5% |
| Average latency | 25.0 to 33.71 ms |
| Requests per observation | 60 to 200 |

The output contains the original measurements
alongside the derived monitoring signals.

[View Signal Results](https://github.com/denisecase/cintel-03-signal-design/blob/main/artifacts/signals.csv)

## Interpretation

Error rate provides a useful indicator of reliability,
while average latency describes responsiveness.

Request counts provide additional context about activity.

Together, these signals offer a more informative view
of system behavior than the raw measurements alone.

## Limitations

The example does not establish acceptable performance
thresholds or evaluate changes over time.

Request counts are not normalized by elapsed time,
so they represent throughput only when observation
intervals are comparable.

## Conclusion

Effective monitoring begins with thoughtful signal design.

Signals should reflect the operational questions
that the monitoring system is intended to answer.

## Documentation Index

- **Home** - this landing page
- [**Project Instructions**](project-instructions.md)
- [**Glossary**](glossary.md)
- [**API**](api.md)
- [**Reactive App**](./app/index.html)

## Project Links

- [GitHub Repository](https://github.com/itsanibose/cintel-03-signal-design-clickstream)
- [Example Pipeline](https://github.com/itsanibose/cintel-03-signal-design-clickstream/blob/main/src/cintel/signal_design.py)
- [Results and Artifacts](https://github.com/itsanibose/cintel-03-signal-design-clickstream/tree/main/artifacts)
- [Project Instructions](project-instructions.md)

## Project Resources

- [Project Instructions](project-instructions.md)
- [Professional Python Guide](https://denisecase.github.io/pro-analytics-02/)
- [Professional Python Project Explainer](https://pup-pack.github.io/professional-python-project-explainer/).
- [Suggested Datasets](https://denisecase.github.io/pro-analytics-02/reference/datasets/cintel/)
