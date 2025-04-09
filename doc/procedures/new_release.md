# How to create a new release

1.  Create a PR from `dev` to `master`: "New release"
2.  Confirm that the development instance works and that the newest changes have been deployed. If not, make a new redeployment of dds-dev (via argocd).

    1. _In general_, e.g. that it's up and running
    2. _Specific feature has been added or changed:_ Confirm that it also works in the development instance
    3. _The change is in the API:_ Confirm that the development instance works together with the CLI

3.  Fork a new branch from `dev` (locally)
4.  Update the version [changelog](../../CHANGELOG.rst), located at `dds_web/CHANGELOG.rst`

    **Tip:** Create a [release **draft**](https://github.com/ScilifelabDataCentre/dds_web/releases/new) with `Target: dev`, click `Generate release notes` and copy paste the release notes into the Changelog. **DO NOT PUBLISH THE RELEASE**

    - The new version should be at the top of the page
    - List the changes that the users will / may notice
    - Do not add information regarding workflow (e.g. GitHub Actions) etc

5.  Update the version in [`version.py`](../../dds_web/version.py)

    - _Minor changes, e.g. bug fix_: Minor version upgrade, e.g. `1.0.1 --> 1.0.2`
    - _Small changes, e.g. new feature_: Mid version upgrade, e.g. `1.1.0 --> 1.2.0`
    - _Breaking changes or large new feature(s)_: Major version upgrade, e.g. `1.0.0 --> 2.0.0` _AVOID THIS -- NEED TO INFORM USERS WELL IN ADVANCE IN THAT CASE SINCE IT WILL BLOCK THE USERS FROM USING ANY OLDER VERSIONS_

      > Will break if CLI version not bumped as well

6.  Push version change to branch
7.  Create a new PR from `<your-branch>` to `dev`: "New version & changelog"

    Wait for approval and merge by Product Owner or admin.

8.  Go back to the PR to `master` ("New release", step 1 above)

    - Are you bumping the major version (e.g. 1.x.x to 2.x.x)?
      - Yes: Add this info to the PR.
    - Do the changes affect the CLI in any way?
      - Yes:
        - Add how the CLI is affected in the PR.
        - Make the corresponding changes to the CLI and create a PR _before_ you merge this PR.
    - _Backward compatibility:_ Check whether or not the dds_cli master branch works with the code in the PR. Note if the dds_web changes work with the previous version of the dds_cli. If something might break - give detailed information about what. **This information should also be included in the MOTD.**
    - All changes should be approved in the PRs to dev so reviewing the changes a second time in this PR is not necessary. Instead, the team should look through the code just to see if something looks weird.
    - All sections and checks in the PR template should be filled in and checked. Follow the instruction in the PR description field.
    - There should be at least one approval of the PR.
    - _Everything looks ok and there's at least one approval?_ Merge it.

9.  [Draft a new release](https://github.com/ScilifelabDataCentre/dds_web/releases)

    1. `Choose a tag` &rarr; `Find or create a new tag` &rarr; Fill in the new version, e.g. if the new version is `1.0.0`, you should fill in `v1.0.0`.
    2. `Target` should be set to `master`
    3. `Release title` field should be set to the same as the tag, e.g. `v1.0.0`
    4. `Write` &rarr; `Generate release notes`.

       You can also fill in something to describe what has been changed in this release, if you feel that the auto-generated release notes are missing something etc.

    5. `Publish release`.

       An image of the web / api will be published to the [GitHub Container Registry](https://codefresh.io/csdp-docs/docs/integrations/container-registries/github-cr/)

10. Perform redeployment during maintenance window.
