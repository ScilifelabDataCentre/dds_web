# How to create a new release

> ### Inform the users of an upcoming release
>
> Always inform users of an upcoming new release _at least_ a week prior to a new release:
>
> 1. Adding a "Message of the Day": `dds motd add`
> 2. Getting the MOTD ID: `dds motd ls`
> 3. Sending the MOTD to the users: `dds motd send [MOTD ID]`

## Automatic Release Drafts

When changes are pushed to `dev` or `master`, a Draft Release is created/updated. The draft will be displayed here: https://github.com/ScilifelabDataCentre/dds_web/releases. The draft will also have a suggestion for what the next version should be, based on PR labels.

## Go through these steps

1.  Confirm that the development instance works and that the newest changes have been deployed. If not, make a new redeployment of dds-dev (via argocd).

    > - Verify that it's up and running.
    > - Confirm that new features / functionality works as it should.
    > - Confirm that the development instance works together with the CLI

2.  Create a PR from `dev` to `master` named "New release: M.M.P" and verify that the PRs included in the changes have the correct labels.

    > Check out the [Release Drafter config file](../../.github/release-drafter.yml) and/or the [PR template](../../.github/pull_request_template.md) for info on which code changes give which labels.

    > Check the release draft: Does the suggestion version seem appropriate? If not: Check the PRs and their labels, again.

    > **Note:** _major version upgrade SHOULD NEVER BE DONE UNLESS THE CLI ALSO HAS THIS IDENTICAL CHANGE_

3.  Fork a new branch from `dev`: `new-version_[new version]` and:

    > - Update the version in [`version.py`](../../dds_web/version.py) and [`tests/test_version.py`](../../tests/test_version.py)
    > - Update the [changelog](../../CHANGELOG.rst): copy-paste the contents of the release draft into the top of the changelog; Follow the same structure/format as previous versions.

    > - Push the `new-version_[new version]` branch to Github and create a new PR from `new-version_[new version]` to `dev`
    > - Verify that the new images look OK. Merge into `dev`

4.  Return to the PR from `dev` to `master`

    > **Do the changes affect the CLI in any way?**
    > If yes:
    >
    > - Add how the CLI is affected in the PR.
    > - Make the corresponding changes to the CLI and create a PR _before_ you merge this PR.
    >
    > **Re: PR approval**
    >
    > - All changes should be approved in the PRs to dev so reviewing the changes a second time in this PR is not necessary.Instead, the team should look through the code just to see if something looks weird.
    > - When there's at least one approval: Merge it.

5.  [Publish the Release Draft](https://github.com/ScilifelabDataCentre/dds_web/releases)

    > A new image is automatically published to GitHub Container Repository (GHCR).

6.  Redeploy the production instance during a maintenance window.

    > Valentin, Alvaro: Please suggest a guide here (if needed). Could be good for new team members.
