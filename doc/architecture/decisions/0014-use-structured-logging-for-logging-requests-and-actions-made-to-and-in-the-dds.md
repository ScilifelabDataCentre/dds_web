# 14. Use structured logging for logging requests and actions made to and in the DDS

Date: 2022-01-12

## Status

Accepted

## Context

When invalid requests or attempts to perform certain actions within the DDS are made, we need an easy and clear way to read this information. 

## Decision

Structured logging should be implemented on the action logging first.

The information required to be logged: username, action, result (failed/successful), time, project in which the action was attempted.

When the action logs have been fixed we will discuss whether or not this will be implemented in the general logging as well, such as debugging and general system info.

## Consequences

<>

## References

Example: ["Structured Logging"](https://newrelic.com/blog/how-to-relic/python-structured-logging)
