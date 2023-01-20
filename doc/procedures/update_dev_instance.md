# How to update the development instance

A new feature should always be tested on the development instance of the DDS **before** it's released in production. When a new feature is added and pushed to the `dev` branch, the development instance (`dds-dev`) should be redeployed.

Redeployments of the development instance can be done at any time. No planning required.

1. Merge change into `dev`. A GitHub action publishes the image
