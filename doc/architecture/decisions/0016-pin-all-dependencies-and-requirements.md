# 16. Pin all dependencies and requirements

Date: 2022-04-14

## Status

Accepted

Supercedes [15. The dependencies should not be pinned](0015-the-dependencies-should-not-be-pinned.md)

## Context

There have been some discussions regarding whether or not we should pin the versions (specify exact versions) of the dependencies installed at startup (in requirements.txt). After some issues, including errors that were difficult to interpret, we finally realised that the issue was in that one of the DDS dependencies had updated to a newer version which was no longer compatible with some of the other dependencies.

## Decision

Pin all versions for all dependencies listed in the requirements.txt, requirements-dev.txt and requirments-tests.txt.

## Consequences

When we bump the versions manually, it will be easier to figure out when the versions are causing issues in the code.
