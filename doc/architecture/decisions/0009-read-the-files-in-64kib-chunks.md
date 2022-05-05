# 9. Read the files in 64KiB chunks

Date: 2020

## Status

Accepted

## Context

Compression and encryption is performed in a streamed manner to avoid reading large files completely in memory. This is performed by reading the file in chunks, and the size of the chunks affect the speed of the algorithms, their memory usage, and the final size of the compressed and encrypted files.

To find the optimal chunk size, a 33 GB file was compressed and encrypted using the chosen algorithms (Zstandard and ChaCha20-Poly1305) after reading the file in different sized chunks ranging from 4 KiB to 500 KiB.

![2020-06-10_17-009_33GB_zstandard-level4_chacha20poly1305](https://user-images.githubusercontent.com/35953392/161818221-2b105fbf-c507-4c87-8783-318ed5b76edb.png)

_Compression ratio is defined as the uncompressed size divided by the compressed size, however, in this case the overhead of the encryption algorithm is also included. Thus here the compression ratio is calculated as the uncompressed size divided by the final size (compressed and encrypted)._

## Decision

Read the files in 64KiB chunks when compressing and encrypting.

## Consequences

64 KiB was chosen since the memory required for the operations increases after 64 KiB, without any significant gain in speed or compression ratio.
