## 1. Description / Summary 

_Add a summary of the changes in this PR and the related issue._

## 2. Jira task / GitHub issue

_Link to the github issue or add the Jira task ID here._

## 3. Type of change

What _type of change(s)_ does the PR contain?

**Check the relevant boxes below. For an explanation of the different sections, enter edit mode of this PR description template.**

- [ ] New feature
  - [ ] Breaking: _Why / How? Add info here._ <!-- Should be checked if the changes in this PR will cause existing functionality to not work as expected. E.g. with the master branch of the `dds_cli` -->
  - [ ] Non-breaking <!-- Should be checked if the changes will not cause existing functionality to fail. "Non-breaking" is just an addition of a new feature. -->
- [ ] Database change: _Remember the to include a new migration version, **or** explain here why it's not needed._ <!-- Should be checked when you've changed something in `models.py`. For a guide on how to add the a new migration version, look at the "Database changes" section in the README.md. -->
- [ ] Bug fix <!-- Should be checked when a bug is fixed in existing functionality. If the bug fix also is a breaking change (see above), add info about that beside this check box. -->
- [ ] Security Alert fix <!-- Should be checked if the PR attempts to solve a security vulnerability, e.g. reported by the "Security" tab in the repo. -->
- [ ] Documentation <!-- Should be checked if the PR adds or updates documentation such as e.g. Technical Overview or a architecture decision (dds_web/doc/architecture/decisions.) -->
- [ ] Workflow <!-- Should be checked if the PR includes a change in e.g. the github actions files (dds_web/.github/*) or another type of workflow change. -->
- [ ] Tests **only** <!-- Should only be checked if the PR only contains tests, none of the other types of changes listed above. -->


<!--
- "Breaking": The change will cause existing functionality to not work as expected.
- Workflow: E.g. a new github action or changes to this PR template. Anything that alters our or the codes workflow.
-->

## Checklist

- [Sprintlog](../SPRINTLOG.md)
  - [ ] Added
  - [ ] Not needed (E.g. PR contains _only_ tests)
- Rebase / Update / Merge _from_ base branch (the branch from which the current is forked)
  - [ ] Done
  - [ ] Not needed
- Blocking PRs
  - [ ] Merged
  - [ ] No blocking PRs
- PR to `master` branch
  - [ ] Yes: Read [the release instructions](https://github.com/ScilifelabDataCentre/dds_web/blob/master/doc/procedures/new_release.md)
    - [ ] I have followed steps 1-8.
  - [ ] No

## Actions / Scans

<!-- Go through all checkboxes. All actions must pass before merging is allowed.-->

- **Black**: Python code formatter. Does not execute. Only tests.
  Run `black .` locally to execute formatting.
  - [ ] Passed
- **Prettier**: General code formatter. Our use case: MD and yaml mainly.
  Run `npx prettier --write .` locally to execute formatting.
  - [ ] Passed
- **Yamllint**: Linting of yaml files.
  - [ ] Passed
- **Tests**: Pytest to verify that functionality works as expected.
  - [ ] New tests added
  - [ ] No new tests
  - [ ] Passed
- **CodeQL**: Scan for security vulnerabilities, bugs, errors
  - [ ] New alerts: _Go through them and either fix, dismiss och ignore. Add reasoning in items below._
  - [ ] Alerts fixed: _What?_
  - [ ] Alerts ignored / dismissed: _Why?_
  - [ ] Passed
- **Trivy**: Security scanner
  - [ ] New alerts: _Go through them and either fix, dismiss och ignore. Add reasoning in items below._
  - [ ] Alerts fixed: _What?_
  - [ ] Alerts ignored / dismissed: _Why?_
  - [ ] Passed
- **Snyk**: Security scanner
  - [ ] New alerts: _Go through them and either fix, dismiss och ignore. Add reasoning in items below._
  - [ ] Alerts fixed: _What?_
  - [ ] Alerts ignored / dismissed: _Why?_
  - [ ] Passed
