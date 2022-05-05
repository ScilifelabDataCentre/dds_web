# 6. Use Zstandard as the compression algorithm

Date: 2020

## Status

Accepted

## Context

Gzip (GNU zip ) is one of the most popular compression algorithms and is suitable for compression of data streams, is supported by all browsers and comes as a standard in all major web servers. However, while gzip provides a good compression ratio , it is very slow compared to other algorithms. Since there is a variety of different compression algorithms it became unreasonable to test every alternative. Instead, prior knowledge about the algorithm Zstandard lead to the choice of comparing gzip with Zstandard. 

## Decision

Use Zstandard as the compression algorithm within DDS.

## Consequences

To test the usefulness of the two options, they were tested in the processing chain together with the chosen encryption algorithm. The encryption speed using ChaCha20-Poly1305 (in mentioned case tested on a 109 MB file) is around 600 MB/s , but when adding compression as a preceding step, the speed was less than 3 MB/s and the compression ratio 3,25. Since the delivery system will be dealing with huge files, it’s important that the processing is efficient, and therefore that the chosen algorithms are fast. Due to this, Zstandard was tested with the same chunk size, resulting in a speed of 119 MB/s and a compression ratio of 3,1. Zstandard thus gave approximately the same compression ratio in a fraction of the time.