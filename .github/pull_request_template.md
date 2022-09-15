> **Before submitting the PR, please go through the seconds below and fill in what you can. If there are any items that are irrelevant for the current PR, remove the row. If a relevant option is missing, please add it as an item and add a PR comment informing that the new option should be included into this template.**

# Description

- [ ] Add a summary of the changes and the related issue
- [ ] Add motivation and context regarding why the change is needed
- [ ] List / describe any dependencies or other changes required for this change
- [ ] Fixes [link to issue / Jira issue ID]

## Type of change

- [ ] Documentation
- [ ] Workflow
- [ ] Security Alert fix
- [ ] Bug fix (non-breaking)
- [ ] New feature (non-breaking)
- [ ] Breaking change (breaking, will cause existing functionality to not work as expected)

# Checklist:

- [ ] Blocking PRs have been merged
- [ ] Rebase / update of branch done
- [ ] Database schema has changed
    - [ ] A new migration is included in the PR
    - [ ] The change does not require a migration
- [ ] Product Owner / Scrum Master
    - [ ] The [version](../dds_web/version.py) is updated (PR to `master` branch)
    - [ ] I am bumping the major version (e.g. 1.x.x to 2.x.x)
        - [ ] I have made the corresponding changes to the CLI version

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
