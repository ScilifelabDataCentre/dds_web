> **Before submitting the PR, please go through the seconds below and fill in what you can. If there are any items that are irrelevant for the current PR, remove the row. If a relevant option is missing, please add it as an item and add a PR comment informing that the new option should be included into this template.**

# Description

In this section:

- [ ] Add a summary of the changes and the related issue
- [ ] Add motivation and context regarding why the change is needed
- [ ] List / describe any dependencies or other changes required for this change
- [ ] If this PR solves an issue, link it (if in GitHub) or add the issue ID (if in Jira). Do this by filling in `[issue link or ID]` below.

Fixes [issue link or ID]

## Type of change

- [ ] Bug fix (non-breaking change which fixes an issue)
- [ ] New feature (non-breaking change which adds functionality)
- [ ] Breaking change (fix or feature that would cause existing functionality to not work as expected)
- [ ] This change requires a documentation update

# Checklist:

Please delete options that are not relevant.

- [ ] Any dependent changes have been merged and published in downstream modules
- [ ] Rebase/merge the branch which this PR is made to
- [ ] Changes to the database schema: A new migration is included in the PR
- [ ] Product Owner / Scrum Master: This PR is made to the `master` branch and I have updated the [version](../dds_web/version.py)
- [ ] I am bumping the major version (e.g. 1.x.x to 2.x.x) and I have made the corresponding changes to the CLI version

## Formatting and documentation

- [ ] I have added a row in the [changelog](../CHANGELOG.md)
- [ ] The code follows the style guidelines of this project: Black / Prettier formatting
- [ ] I have performed a self-review of my code
- [ ] I have commented my code, particularly in hard-to-understand areas
- [ ] I have made corresponding changes to the documentation
- [ ] My changes generate no new warnings

## Tests

- [ ] I have added tests that prove my fix is effective or that my feature works
- [ ] New and existing unit tests pass locally with my changes
