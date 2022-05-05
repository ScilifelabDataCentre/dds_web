# 8. Encrypt all files with ChaCha20-Poly1305

Date: 2020

## Status

Accepted

## Context

In the KTH SciLifeLab Use Case report it was stated that encryption within the Data Delivery System would be performed with the `crypt4gh` tool, the current cryptographic standard for genomics and health developed by the Global Alliance for Genomics and Health (GA4GH). Although there are many advantages of using this file format, there are a number of different disadvantages:

- Does not protect against insertions, deletions or reordering. The MACs represent a block each, not the entire file [20].
- Does not provide any way of authenticating the files – the sending and receiving parties identities cannot be proven. The reader cannot know who has encrypted and sent the file, and the writer cannot know who decrypts and reads the file.
- Although the possibility of file access by multiple users and random access is useful in many cases, for delivery purposes these features are not important and do not help.
- For encryption to begin, all previous operations such as compression, need to be finished. This means that the files need to be processed from start to end multiple times, leading to a large increase in delivery time. This will be specially evident for large or even huge files, which will be common in the delivery system.
- It may have been possible to alter the crypt4gh package code to enable streaming (tested without success), however the file format does not provide simplifying properties for our purposes

Ref:

- [Crypt4GH: A secure method for sharing human genetic data](https://www.ga4gh.org/news/crypt4gh-a-secure-method-for-sharing-human-genetic-data/)
- [Crypt4GH utility — GA4GH cryptor](https://crypt4gh.readthedocs.io/en/latest/)

When attempting to solve the different problems, switching to one of the algorithms `AES-256-GCM` or `ChaCha20-Poly1305` was discussed.

## Decision

Use ChaCha20-Poly1305 to encrypt the files being delivered with the DDS.

## Consequences

`AES` (the Advanced Encryption Standard), is a block cipher which combines the core algorithm with a mode of operation – techniques on how to process sequences of data blocks. In this case the mode is the Galois Counter Mode (GCM), and authenticated Encryption with Associated Data (AEAD) mode. One of the biggest advantages of using `AES-256-GCM` is that it is the most widely used (and therefore highly trusted) authenticated cipher, however some hurdles come with using it:

- Nonce repetition reduces the security drastically – tags can be forged
- Not as fast in software implementations
- Easy to get wrong
- Vulnerable to cache-timing attacks

Ref:

- [Using AES-CCM and AES-GCM Authenticated Encryption in the Cryptographic Message Syntax (CMS)](https://tools.ietf.org/html/rfc5084)
- S. J. Nielson and C. K. Monson, Practical Cryptography in Python. 2019

`ChaCha20-Poly1305` is a stream cipher and is the algorithm used within the `crypt4gh` tool. `ChaCha20-Poly1305` is also (in addition to `AES-GCM`) an AEAD algorithm, and combines the encryption algorithm `ChaCha20` with the authentication algorithm `Poly1305`. The advantages and disadvantages of using `ChaCha20-Poly1305` for encryption in the Data Delivery System is listed below.

---

**Advantages**

- Is based on the ARX design – does not use substitution boxes as AES does and therefore does not produce cache footprints. It is therefore not vulnerable to cache-timing attacks.
- Fast in software implementations. Multiple times faster than AES.
- The security is currently considered to be at least as secure as AES-GCM
- Intrinsically simpler than AES
- Easier to implement and not as easy to get wrong
- Used in Crypt4GH file format – the encryption format standard for genomics and health related data
- Part of the Internet Engineering Task Force (IETF) for secure network protocols IPSec, SSH, TLS

**Disadvantages**

- Not the general standard
- Has not undergone as much cryptanalysis as AES and may therefore be vulnerable to attacks which are currently unknown
- May not be available for encryption of files uploaded via the web interface.

---

During these comparisons we found that the advantages of ChaCha20-Poly1305 overweighed the advantages of using AES-256-GCM. Since files delivered within the system can be huge, it is important to choose a format or algorithm which has a high message size limit, is as fast and secure as possible for all file sizes, and has the least possible risk of implementation error. ChaCha20 fulfills this, and is in addition supported by both the Global Alliance for Genomics and Health, and IETF secure network protocols. Although ChaCha20 is not the general encryption standard, it is becoming increasingly more used, becoming favored over AES in certain aspects and so far cryptanalysis have not (to our knowledge) found any vulnerabilities that are deal-breakers. The ”issue” regarding client-side encryption in the browser for the web interface may not be an issue since client-side encryption in browsers are generally not recommended. In addition, it is not decided whether or not the files uploaded via the web interface will be encrypted or if the users attempting this will be directed to the CLI when handling any type of sensitive data. These points are still under investigation and discussion. However, if encryption in the browser would be decided, this could be solved in one of the following ways:

- HTTPS will be used, which is secured via TLS. If TLS is deemed to give enough protection to the uploaded data from the browser to the server, ChaCha20 encrypts the files once they have reached the server and uploads them to Safespring S3 in a similar way as the CLI.
- If an extra layer of security is needed, encryption can be performed in the browser using AES-GCM. Information on the algorithm used per specific file will be added to the database.

Due to this, ChaCha20-Poly1305 was chosen as the encryption algorithm within the Data Delivery System. The algorithm description does not include how the data encryption key will be distributed in a secure manner – this will be handled in a similar way to the Crypt4GH format, but the public keys will be uploaded to the database and not saved within the files.

Ref: [ChaCha20 and Poly1305 for IETF Protocols](https://tools.ietf.org/html/rfc7539)
