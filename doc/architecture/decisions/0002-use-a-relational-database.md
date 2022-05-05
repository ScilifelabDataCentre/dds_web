# 2. Use a relational database

Date: 2020

## Status

Accepted

## Context

The initial database used in the beginning of the development was the non-relational CouchDB. Later it was investigated whether this was the best approach or whether a relational database was better for the systems purposes.

## Decision

Use a **relational** database for the DDS.

## Consequences

A relational database means that we are forced to keep it structured. A relational database can also be more efficient than non-relational databases when used in the correct way. Also, the security and data integrity are important aspects.

## References

[SQL vs NoSQL Exact Difference](https://www.softwaretestinghelp.com/sql-vs-nosql/)
