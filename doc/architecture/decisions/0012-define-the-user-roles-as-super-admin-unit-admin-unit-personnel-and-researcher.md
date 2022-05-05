# 12. Define the user roles as Super Admin, Unit Admin, Unit Personnel and Researcher

Date: 2021-09-14

## Status

Accepted

## Context

Only certain users should be able to upload, create projects etc. 

## Decision

### Super Admin (DC)

* Manage: Add, Remove, Edit
   * Unit (instances)
   * Users
 
### Unit Admin
* Unit Personnel Permissions
* Manage: Add, Add to project, Remove from project, Remove account, Change permissions
    * Unit Admin
    * Unit User

### Unit Personnel
* Project Owner Permissions
* Upload
* Delete

### Research Account
* Remove own account
* List
* Download

#### Project Owner
* Research User Permissions
* Manage: Invite, Add to project, Remove from project, Remove account, Change permissions
    * Project Owners
    * Research Users

## Consequences

<>
