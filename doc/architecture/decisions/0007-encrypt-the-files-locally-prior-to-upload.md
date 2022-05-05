# 7. Encrypt the files locally prior to upload

Date: 2020

## Status

Accepted

## Context

The optimal way of delivering the data to the owners would be to perform encryption- and decryption in-transit, thereby decreasing the amount of memory required locally and possibly the total delivery time. However, there have been some difficulties finding a working solution for this, including that the `crypt4gh` Python package used in the beginning of the development did not support it. On further investigation and contact with Safespring, we learned:
* Server-side encryption (and server-side stored keys) is technically possible on Safespring S3 storage but Safespring has chosen to not activate that function. 
* Most of the S3- and Boto clients that Safespring uses, e.g. the bash cli s3cmd, goes through GPG  which performs the encryption before uploading the files. GPG/PGP makes it possible to encrypt using one key and decrypt using one or more other keys. This enables a more automated process but does not simplify for us or contribute with anything useful to the delivery system. 
* All users of the Safespring backup service perform encryption on their own and handle the keys themselves. 

## Decision

Encrypt all files locally prior to uploading them.

## Consequences

Extra space on the client computer or server is required.
