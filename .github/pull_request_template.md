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

## General

- [ ] [Changelog](../CHANGELOG.md): New row added
- [ ] Database schema has changed
  - [ ] A new migration is included in the PR
  - [ ] The change does not require a migration
- [ ] Code change
  - [ ] Self-review of code done
  - [ ] Comments added, particularly in hard-to-understand areas
  - [ ] Documentation is updated

## Repository / Releases

- [ ] Blocking PRs have been merged
- [ ] Rebase / update of branch done
- [ ] Product Owner / Scrum Master
  - [ ] The [version](../dds_web/version.py) is updated (PR to `master` branch)
  - [ ] I am bumping the major version (e.g. 1.x.x to 2.x.x)
    - [ ] I have made the corresponding changes to the CLI version

## Checks

- [ ] Formatting: Black & Prettier checks pass
- [ ] Tests
  - [ ] I have added tests for the new code
  - [ ] The tests pass
- [ ] Trivy:
  - [ ] There are no new security alerts 
  - [ ] This PR fixes new security alerts
  - [ ] Security alerts have been dismissed
  - [ ] PR will be merged with new security alerts; This is why: _Please add a short description here_
