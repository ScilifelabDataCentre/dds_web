# How to update the development instance

A new feature should always be tested on the development instance of the DDS **before** it's released in production. When a new feature is added and pushed to the `dev` branch, the development instance (`dds-dev`) should be redeployed.

Redeployments of the development instance can be done at any time. No planning required.

1.  Merge change into `dev`. A GitHub action publishes the image to GHCR.
2.  Ask the sysadmins for a redeployment.

    1.  Go to the [sysadmin repository](https://github.com/ScilifelabDataCentre/sysadmin/issues)
    2.  Create a new issue and fill in the following information

        `Title`

            DDS: Redeploy the development instance (`dds-dev`)

        `Leave a comment`

            Please redeploy the dev instance of the DDS.
