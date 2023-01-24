# How to create a new release

**Is the release planned for the next cluster maintenance?** Please read point 8 first.

1.  Confirm that the development instance works

    1. _In general_, e.g. that it's up and running
    2. _Specific feature has been added or changed:_ Confirm that it also works in the development instance
    3. _The change is in the API:_ Confirm that the development instance works together with the CLI

2.  Fork a new branch from `dev`
3.  Update the version in [`version.py`](../../dds_web/version.py)

    - _Minor changes, e.g. bug fix_: Minor version upgrade, e.g. `1.0.1 --> 1.0.2`
    - _Small changes, e.g. new feature_: Mid version upgrade, e.g. `1.1.0 --> 1.2.0`
    - _Breaking changes or large new feature(s)_: Major version upgrade, e.g. `1.0.0 --> 2.0.0`

      > Will break if CLI version not bumped as well

4.  Push version change to branch
5.  Create a new PR from `<your-branch>` to `dev`

    Wait for approval and merge by Product Owner or admin.

6.  Create a PR from `dev` to `master`

    - _Backward compatibility:_ Check whether or not the dds_cli master branch works with the code in the PR. There’s an item in the PR comment regarding this; note if the dds_web changes work with the previous version of the dds_cli. If something might break - give detailed information about what. **This information should also be included in the MOTD.**
    - All changes should be approved in the PRs to dev so reviewing the changes a second time in this PR is not necessary. Instead, the team should look through the code just to see if something looks weird.
    - All sections and checks in the PR template should be filled in and checked. Follow the instruction in the PR description field.
    - There should be at least one approval of the PR.
    - _Everything looks ok and there's at least one approval?_ Merge it.

7.  [Draft a new release](https://github.com/ScilifelabDataCentre/dds_web/releases)

    1. `Choose a tag` &rarr; `Find or create a new tag` &rarr; Fill in the new version, e.g. if the new version is `1.0.0`, you should fill in `v1.0.0`.
    2. `Target` should be set to `master`
    3. `Release title` field should be set to the same as the tag, e.g. `v1.0.0`
    4. `Write` &rarr; `Generate release notes`.

       You can also fill in something to describe what has been changed in this release, if you feel that the auto-generated release notes are missing something etc.

    5. `Publish release`.

       An image of the web / api will be published to the [GitHub Container Registry](https://codefresh.io/csdp-docs/docs/integrations/container-registries/github-cr/)

8.  Perform redeployment

    The method for this _depends on the situation_ / size of and reason for the upgrade.

    - **Bug**, affecting the DDS functionality - Fix ASAP

      1.  Add a new _Message of the Day_ (MOTD) informing the users of an ongoing / immediate update - (see CLI)
      2.  Send the MOTD via email (see CLI)
      3.  Send a message in the `dds-status` slack channel to inform the units
      4.  Ask for a redeployment

          1.  Go to the [sysadmin repository](https://github.com/ScilifelabDataCentre/sysadmin/issues)
          2.  Create a new issue and fill in the following information

              `Title`

                  DDS: Redeploy the production instance (`dds`)

              `Leave a comment`

                  Please redeploy the production instance of the DDS.
                  Image: <Name of the latest release / tag, e.g. v1.1.0 >

                  Fill in the [manual log](https://scilifelab.atlassian.net/wiki/spaces/deliveryportal/pages/2318565390/Production) on Confluence.

    - **New feature** or bug that does not need an immediate fix

      Cluster maintenance is performed the first Wednesday (that is a work day) of every month. The DDS is redeployed during this as well. However, we still need to inform the users of the upcoming upgrade, and the sysadmins of which image they should deploy.

      1.  Go to the [sysadmin repository](https://github.com/ScilifelabDataCentre/sysadmin/issues)
      2.  Create a new issue and fill in the following information

          `Title`

              DDS: Schedule redeployment of production instance (`dds`) for next cluster maintenance window

          `Leave a comment`

              During the next cluster maintenance (`<Weekday, Day / Month, Time>`), please redeploy the production instance of the DDS.

              Image: <Name of the latest release / tag, e.g. v1.1.0 >

              Fill in the [manual log](https://scilifelab.atlassian.net/wiki/spaces/deliveryportal/pages/2318565390/Production) on Confluence.
