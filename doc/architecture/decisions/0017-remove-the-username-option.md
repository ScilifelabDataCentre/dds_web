# 17. Remove the --username option

Date: 2022-03-02

## Status

Accepted

## Context

Previously there was a --username option for all commands where the user could specify the username.

## Decision

Remove the `--username` option from the CLI.

## Consequences

When using dds auth login command, either the existing encrypted token will be used or the user will be prompted to fill in the username and password.
