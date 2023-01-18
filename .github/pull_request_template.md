<!--
> **Before _submitting_ PR:**
>
> - Fill in and tick fields
> - _Remove all rows_ that are not relevant for the current PR
>   - Revelant option missing? Add it as an item and add a PR comment informing that the new option should be included into this template.
>
> **Before _merging_ PR:** 
> 
> _Tick all relevant items._
-->
# Description

### **1. This PR contains the following changes...**

_Add a summary of the changes and the related issue._

### **2. The following additional changes are required for this to work**

_Add information on additional changes required for the PR changes to work, both locally and in the deployments._
> E.g. Does the deployment setup need anything for this to work?

### **3. The PR fixes the following GitHub issue / Jira task**

<!-- Comment out the item which does not apply here.-->

- [ ] GitHub issue (link): 
- [ ] Jira task (ID, `DDS-xxxx`): 

### **4. What _type of change(s)_ does the PR contain?**

<!-- 
- "Breaking": The change will cause existing functionality to not work as expected.
- Workflow: E.g. a new github action or changes to this PR template. Anything that alters our or the codes workflow.
-->

- [ ] New feature
  - [ ] Breaking: _Please describe the reason for the break and how we can fix it._
  - [ ] Non-breaking
- [ ] Database change
  - [ ] Migration _included in PR_
  - [ ] Migration _not needed_ 
- [ ] Bug fix
  - [ ] Breaking: _Please describe the reason for the break and how we can fix it._
  - [ ] Non-breaking
- [ ] Security Alert fix
- [ ] Documentation
- [ ] Tests **(only)**
- [ ] Workflow

# Checklist to go through...

<!-- Comment out the items which do not apply here.-->

### **Always**

<!-- Always go through the following items. If they do not apply, comment them out -->
| Item                                       | Options                                                     | Note                                                                |
|--------------------------------------------|-----------------------------------|---------------------------------------------------------------------|
| [Changelog](../CHANGELOG.md)               | <ul><li>- [ ] Added</li></ul>                       | Not needed when PR includes _only_ tests.                           |
| Rebase / Update / Merge _from_ base branch | <ul><li>- [ ] Done</li><li>- [ ] Not needed</li></ul>  |                                                                     | 
| Blocking PRs                               | <ul><li>- [ ] Merged</li></ul>                      | Must be checked if functionality in current PR relies on another PR |
| PR to `master` branch                      | <ul><li>- [ ] Yes</li><li>- [ ] No</li></ul>           | If **Yes**: Go through the section [PR to master](#pr-to-master)    |

### If PR consists of **code change(s)**

<!-- If the PR contains code changes, the following need to be checked.-->
| Item                         | Options                               | Note                                               |
|------------------------------|---------------------------------------|----------------------------------------------------|
| Self-review done             | <ul><li>- [ ] Yes</li></ul>                             | Checked item required for all code changes         |
| Comments, docstrings etc.    | <ul><li>- [ ] Added</li></ul>                           | Particularly important in hard-to-understand areas |
| Documentation                | <ul><li>- [ ] Updated </li><li> - [ ] Not needed</li></ul>   |                                                    |

### If PR is to **master**

<!-- Is your PR to the master branch? The following items need to be checked off. -->
- [ ] I have followed steps 1-5 in [the release instructions](../doc/procedures/new_release.md)
- [ ] I am bumping the major version (e.g. 1.x.x to 2.x.x)
- [ ] I have made the corresponding changes to the CLI version


**Is this version _backward compatible?_**

- [ ] Yes: The code works together with `dds_cli/master` branch
- [ ] No: The code **does not** entirely / at all work together with the `dds_cli/master` branch. _Please add detailed and clear information about the broken features_


### **6. Actions / Scans**

| Action   | What                                                      | Note                                                                            | OK    |
|----------|-----------------------------------------------------------|---------------------------------------------------------------------------------|-------|
| Black    | Python code formatter. Does not execute.                  |                                                                                 | <ul><li>- [ ] </li></ul> |
| Prettier | General code formatter. Our use case: MD and yaml mainly. |                                                                                 | <ul><li>- [ ] </li></ul> |
| Tests    | Pytest to that verify functionality works as expected.    | New tests... <ul><li>- [ ] Added </li><li> - [ ] Not needed </li></ul>                             | <ul><li>- [ ] </li></ul> |
| CodeQL   | Scan for security vulnerabilities, bugs, errors           |                                                                                 | <ul><li>- [ ] </li></ul> |
| Trivy    | Security scanner                                          | Alert(s) fixed <ul><li> - [ ] Yes: _What?_ </li><li> - [ ] No (incl. dismissed): _Why?_ </li></ul>  | <ul><li>- [ ] </li></ul> |
| Snyk     | Security scanner                                          | Alert(s) fixed <ul><li> - [ ] Yes: _What?_ </li><li> - [ ] No (incl. dismissed): _Why?_ </li></ul>  | <ul><li>- [ ] </li></ul> |

