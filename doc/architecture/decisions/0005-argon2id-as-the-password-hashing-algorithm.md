# 5. Argon2id as the password hashing algorithm

Date: 2021

## Status

Accepted

Supercedes [4. Scrypt as the password hashing algorithm](0004-scrypt-as-the-password-hashing-algorithm.md)

## Context

Since the Data Delivery System is aimed at handing large amounts of sensitive information, it’s important that the access to the system is controlled and validated in a secure manner. Simply hashing the passwords and saving the results is certainly not enough to guarantee this level of security, nor is salting the passwords before hashing. To handle the user accounts passwords, the algorithms `Scrypt`, `Bcrypt` and `Argon2` were discussed. These also include steps such as salting etc., however, they include additional steps, making them more resistant to multiple types of attacks, and are considered to be secure key derivation functions.

## Decision

Use Argon2id as the password hashing algorithm.

## Consequences

In the Alpha Version of the Data Delivery System, `Scrypt` was used via the Python `cryptography` package. The change has now been made to `Argon2`. Both `Scrypt` and `Argon2` are cryptographically secure KDFs, however `Argon2` is generally recommended over `Scrypt` since it's ASIC (specialized hardware) resistant and GPU (graphics cards) resistant, and has a better password cracking resistance than the other KDFs for similar configuration parameters for CPU and RAM usage. [KDF Info](https://wizardforcel.gitbooks.io/practical-cryptography-for-developers-book/content/mac-and-key-derivation/modern-key-derivation-functions.html)

## References
* [Scrypt - Practical Cryptography for Developers](https://wizardforcel.gitbooks.io/practical-cryptography-for-developers-book/content/mac-and-key-derivation/scrypt.html)
* [Bcrypt - Practical Cryptography for Developers](https://wizardforcel.gitbooks.io/practical-cryptography-for-developers-book/content/mac-and-key-derivation/bcrypt.html)
* [Argon2 - Practical Cryptography for Developers](https://wizardforcel.gitbooks.io/practical-cryptography-for-developers-book/content/mac-and-key-derivation/argon2.html)