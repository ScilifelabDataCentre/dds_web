# 13. Have one-time code via email as the default 2FA method

Date: 2021-12-01

## Status

Accepted

## Context

Initially, TOTP was implemented as the Two Factor Authentication. Authentication apps such as Authy or Google Authenticator could be set up and used to identify a user. However, due to some technical difficulties for some users, we needed to discuss whether or not we should have the apps or a one-time code via email as the default method. 

## Decision

Set one-time code via email as the default 2FA method (HOTP)

## Consequences
2FA with authenticator apps (with TOTP) will be implemented at some point and the users will be able to choose which method they want to use.
