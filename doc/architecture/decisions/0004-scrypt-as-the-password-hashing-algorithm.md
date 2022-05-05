# 4. Scrypt as the password hashing algorithm

Date: 2020

## Status

Superceded by [5. Argon2id as the password hashing algorithm](0005-argon2id-as-the-password-hashing-algorithm.md)

## Context

Since the Data Delivery System is aimed at handing large amounts of sensitive information, it’s important that the access to the system is controlled and validated in a secure manner. Simply hashing the passwords and saving the results is certainly not enough to guarantee this level of security, noris salting the passwords before hashing. To  handle  the user  accounts  passwords, the  algorithms scrypt52, bcrypt53and Argon254were  discussed. These also include steps such as salting etc. however they include additional steps, making them more resistant to multiple types of attacks, and are considered to be secure key derivation functions.

### Scrypt
* Strong cryptographic key-derivation function (KDF)
* Memory-intensive
* Designed to prevent GPU, ASIC and FPGA attacks

> “It  is  considered  that Scrypt  is more   secure   than   Bcrypt,so modern   applications   should prefer Scrypt(or Argon2) instead of Bcrypt.”

### Bcrypt
* Secure KDF•Older than Scrypt
* Less resistant to ASIC and GPUattacks
* Uses constant memory and is therefor easier to crack

### Argon2
* Highly secure KDF function
* ASIC-and GPU-resistant
* Better password cracking resistance than Bcrypt and Scrypt

> “In  the  general  case Argon2  is recommendedover Scrypt[and]Bcrypt[...]”

## Decision

Use Scrypt as the password hashing algorithm. The default values are used.

## Consequences

In the current version of the Data Delivery System, Scryptis usedvia the Python cryptographypackage. The plan is tochange to Argon2, provided that the package mentioned in the link below is deemed  to  be appropriate, or that an alternative Python package is found. This has not been investigated yet since Scrypt is considered to provide a high level of security and focus has been on developing other key parts of the system.

Scrypt is, as mentioned, memory-intensive, meaning that the cost is high to perform the key derivation. This is not an issue when performing the operation once(as in normal login procedures),however in the case of hackers attemptingto crack the password, the high amount of memory (and time depending on the n-parameter value)required results in the hacking becoming very costly. Thus the goal of the algorithm is to make hacking the passwords as inconvenient and impractical as possible.

## References
* Scrypt
    * https://tools.ietf.org/html/rfc7914.html
    * https://wizardforcel.gitbooks.io/practical-cryptography-for-developers-book/content/mac-and-key-derivation/scrypt.html
* Bcrypt
    * https://wizardforcel.gitbooks.io/practical-cryptography-for-developers-book/content/mac-and-key-derivation/bcrypt.html
* Argon2
    * https://wizardforcel.gitbooks.io/practical-cryptography-for-developers-book/content/mac-and-key-derivation/argon2.html
