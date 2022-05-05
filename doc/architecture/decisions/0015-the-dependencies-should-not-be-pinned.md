# 15. The dependencies should not be pinned

Date: 2022-03-01

## Status

Superceded by [16. Pin all dependencies and requirements](0016-pin-all-dependencies-and-requirements.md)

## Context

There have been some discussions regarding whether or not we should pin the versions (specify exact versions) of the dependencies installed at startup (in requirements.txt).

## Decision

We will not pin the requirement versions. 

## Consequences

If at some point something stops working we will look into it then and update the requirements then. This will simplify the installation for the users which is one of our priorities.
