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

### **This PR contains the following changes...**

_Add a summary of the changes and the related issue._

### **The following additional changes are required for this to work**

_Add information on additional changes required for the PR changes to work, both locally and in the deployments._
> E.g. Does the deployment setup need anything for this to work?

### **The PR fixes the following GitHub issue / Jira task**

<!-- Comment out the item which does not apply here.-->

- [ ] GitHub issue (link): 
- [ ] Jira task (ID, `DDS-xxxx`): 

### **What _type of change(s)_ does the PR contain?**

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

# Checklist:

<!-- Comment out the items which do not apply here.-->

### **Always**

| Item                                       | Options                                                     | Note                                                                |
|--------------------------------------------|-----------------------------------|---------------------------------------------------------------------|
| [Changelog](../CHANGELOG.md)               | - [ ] Added                       | Not needed when PR includes _only_ tests.                           |
| Rebase / Update / Merge _from_ base branch | - [ ] Done <br> - [ ] Not needed  |                                                                     | 
| Blocking PRs                               | - [ ] Merged                      | Must be checked if functionality in current PR relies on another PR |
| PR to `master` branch                      | - [ ] Yes <br> - [ ] No           | If **Yes**: Go through the section [PR to master](#pr-to-master)    |

### **Code change**

| Item                         | Options                               | Note                                               |
|------------------------------|---------------------------------------|----------------------------------------------------|
| Self-review done             | - [ ] Yes                             | Checked item required for all code changes         |
| Comments, docstrings etc.    | - [ ] Added                           | Particularly important in hard-to-understand areas |
| Documentation                | - [ ] Updated <br> - [ ] Not needed   |                                                    |

### **PR to master**

- [ ] I have followed steps 1-5 in [the release instructions](../docs/procedures/new_release.md)
- [ ] I am bumping the major version (e.g. 1.x.x to 2.x.x)
- [ ] I have made the corresponding changes to the CLI version

**Backward compatibility**

Is this version backward compatible? 

- [ ] Yes: The code works together with `dds_cli/master` branch
- [ ] No: The code **does not** entirely / at all work together with the `dds_cli/master` branch. _Please add detailed and clear information about the broken features_


## Actions / Scans

| Action   | What                                                      | Note                                                                            | OK    |
|----------|-----------------------------------------------------------|---------------------------------------------------------------------------------|-------|
| Black    | Python code formatter. Does not execute.                  |                                                                                 | - [ ] |
| Prettier | General code formatter. Our use case: MD and yaml mainly. |                                                                                 | - [ ] |
| Tests    | Pytest to that verify functionality works as expected.    | New tests... <br> - [ ] Added <br> - [ ] Not needed                             | - [ ] |
| CodeQL   | Scan for security vulnerabilities, bugs, errors           |                                                                                 | - [ ] |
| Trivy    | Security scanner                                          | Alert(s) fixed <br> - [ ] Yes: _What?_ <br> - [ ] No (incl. dismissed): _Why?_  | - [ ] |
| Snyk     | Security scanner                                          | Alert(s) fixed <br> - [ ] Yes: _What?_ <br> - [ ] No (incl. dismissed): _Why?_  | - [ ] |

