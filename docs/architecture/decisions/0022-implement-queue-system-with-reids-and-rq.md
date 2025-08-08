# 22. Implement queue system with Redis and RQ

Date: 2024

## Status

Accepted

## Context

For a considerable amout of time, DDS has been expericing issues when too many requests are made to the API (backend). In some cases, even timeouts occur, due to them taking a considerable time. Solutions were discussed, related with implementing a queuing system, so that requests can be scheduled and executed in a non-serial manner.

## Decision

Different alternatives were discused. However, because the system already uses Redis as storage. And it has queue features, it was decided to implement it on top of Redis using the library `RQ`.

## Consequences

Some endpoints were `enqued`. Including:

1. MOTD (Message of The Day).
2. Remove data (dds data rm).
3. Delete projects.
4. Archive projects.

A dashborad is available at `https://delivery.scilifelab.se/rq` (requires VPN) to visualize the status of the operations.

## References

[RQ documentation](https://python-rq.org/docs/)

[Dashboard](https://delivery.scilifelab.se/rq)
