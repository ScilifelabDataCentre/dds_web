# API Endpoints and their status code reponses

## Authentication

- `401 Unauthorized`
  - Incorrect username or password
  - Expired token
  - Invalid token
  - Incorrect role
  - Password reset after last authenticated token generated
  - Two Factor Authentication not provided
- `403 Forbidden`
  - User is deactivated

---

## Utils

- `400 Bad Request`
  - Invalid email type

---

## `files.py`

### NewFile

#### `post`

- [Authentication errors](#authentication)
- `400 Bad Request`
  - Decorators
    - Json required but not provided
    - Validation error
  - Schemas
    - Project does not exist
  - Incorrect project status for upload
- `403 Forbidden`
  - Schemas
    - User does not have access to project
- `500 Internal Server Error`
  - Database errors

#### `put`

- [Authentication errors](#authentication)
- `400 Bad Request`
  - Decorators
    - Validation error
  - Schemas
    - Project does not exist
  - Json required but not provided / All required fields not provided
  - Incorrect project status for upload
  - Trying to overwrite a file but file not found in database
- `403 Forbidden`
  - Schemas
    - User does not have access to project
- `500 Internal Server Error`
  - Database errors

### MatchFiles

- [Authentication errors](#authentication)
- `400 Bad Request`
  - Decorators
    - Json required but not provided
    - Validation error
  - Schemas
    - Project does not exist
  - Incorrect project status for upload
- `403 Forbidden`
  - Schemas
    - User does not have access to project
- `500 Internal Server Error`
  - Database errors

### ListFiles

- [Authentication errors](#authentication)
- `400 Bad Request`
  - Decorators
    - Validation error
  - Schemas
    - Project does not exist
- `403 Forbidden`
  - Schemas
    - User does not have access to project
  - Researcher trying to download data from 'In Progress' project
- `500 Internal Server Error`
  - Database errors

### RemoveFile

- [Authentication errors](#authentication)
- `400 Bad Request`
  - Decorators
    - Json required but not provided
    - Validation error
  - Schemas
    - Project does not exist
  - Project is not 'In Progress'
  - Project has previously been made 'Available'
- `403 Forbidden`
  - Schemas
    - User does not have access to project

### RemoveDir

- [Authentication errors](#authentication)
- `400 Bad Request`
  - Decorators
    - Json required but not provided
    - Validation error
  - Schemas
    - Project does not exist
  - Project is not 'In Progress'
  - Project has previously been made 'Available'
- `403 Forbidden`
  - Schemas
    - User does not have access to project
- `500 Internal Server Error`
  - Database errors

### FileInfo

- [Authentication errors](#authentication)
- `400 Bad Request`
  - Decorators
    - Json required but not provided
    - Validation error
  - Schemas
    - Project does not exist
    - The project does not contain any data
  - Project is not 'Available' and downloader is Researcher
  - No files requested for download
- `403 Forbidden`
  - Schemas
    - User does not have access to project
- `500 Internal Server Error`
  - S3 connection errors

### FileInfoAll

- [Authentication errors](#authentication)
- `400 Bad Request`
  - Decorators
    - Validation error
  - Schemas
    - Project does not exist
    - The project does not contain any data
- `403 Forbidden`
  - Schemas
    - User does not have access to project
- `500 Internal Server Error`
  - S3 connection errors

### UpdateFile

- [Authentication errors](#authentication)
- `400 Bad Request`
  - Decorators
    - Json required but not provided
    - Validation error
  - Schemas
    - Project does not exist
  - Trying to update a file but file name not provided
  - Trying to update a file which is not found in database
- `403 Forbidden`
  - Schemas
    - User does not have access to project
- `500 Internal Server Error`
  - Database errors

---

## `project.py`

### CreateProject

- [Authentication errors](#authentication)
- [AddUser errors](#adduser)
- `400 Bad Request`
  - Decorators
    - Json required but not provided
    - Validation error
  - Missing required info or wrong format
  - No user invites sent
- `403 Forbidden`
  - Less than 2 Unit Admins
- `500 Internal Server Error`
  - User / Project Key errors (any)
  - Database errors
  - S3 connection errors

### ProjectStatus

#### `get`

- [Authentication errors](#authentication)
- `400 Bad Request`
  - Decorators
    - Validation error
  - Schemas
    - Project does not exist
- `403 Forbidden`
  - Schemas
    - User does not have access to project

#### `post`

- [Authentication errors](#authentication)
- `400 Bad Request`
  - Decorators
    - Json required but not provided
    - Validation error
  - Schemas
    - Project does not exist
  - Missing required status info
  - Invalid new status
  - Invalid status transition
  - `release_project`
    - Invalid deadline
    - Max number of times available reached
  - `expire_project`
    - Invalid deadline
  - `delete_project`
    - Trying to delete project which has been availble
  - `archive_project`
    - Trying to archive a project which has been previously made available
- `403 Forbidden`
  - Schemas
    - User does not have access to project
- `500 Internal Server Error`
  - Database errors
  - `delete_project`
    - Database or S3 issues
  - `archive_project`
    - Database or S3 issues

#### `patch`

- [Authentication errors](#authentication)
- `400 Bad Request`
  - Decorators
    - Json required but not provided
    - Validation error
  - Schemas
    - Project does not exist
  - Project is busy
  - `extend_deadline`
    - Invalid deadline
    - No deadline provided
    - Project is not in Available state
    - Max number of times available reached
- `403 Forbidden`
  - Schemas
    - User does not have access to project
- `500 Internal Server Error`
  - Database errors
  - `delete_project`
    - Database or S3 issues
  - `archive_project`
    - Database or S3 issues

### GetPublic

- [Authentication errors](#authentication)
- `400 Bad Request`
  - Decorators
    - Validation error
  - Schemas
    - Project does not exist
- `403 Forbidden`
  - Schemas
    - User does not have access to project
- `500 Internal Server Error`
  - No public key found for project

### GetPrivate

- [Authentication errors](#authentication)
- `400 Bad Request`
  - Decorators
    - Validation error:
  - Schemas
    - Project does not exist
- `403 Forbidden`
  - Schemas
    - User does not have access to project
- `500 Internal Server Error`
  - User / Project Key errors (any)

### UserProjects

- [Authentication errors](#authentication)
- `500 Internal Server Error`
  - Database errors

### RemoveContents

- [Authentication errors](#authentication)
- `400 Bad Request`
  - Decorators
    - Validation error
  - Schemas
    - Project does not exist
  - Incorrect status
  - Nothing to delete in project
- `403 Forbidden`
  - Schemas
    - User does not have access to project
- `500 Internal Server Error`
  - Decorators
    - Database errors
  - Database or S3 issues

### ProjectUsers

- [Authentication errors](#authentication)
- `400 Bad Request`
  - Decorators
    - Validation error
  - Schemas
    - Project does not exist
- `403 Forbidden`
  - Schemas
    - User does not have access to project

### ProjectAccess

- [Authentication errors](#authentication)
- `400 Bad Request`
  - Decorators
    - Validation error
    - Json required but not provided
  - Schemas
    - Project does not exist
  - Required email adress missing
  - User getting access does not exist
- `403 Forbidden`
  - Schemas
    - User does not have access to project
  - Attempting to renew your own project access
  - Attempting to renew access for invalid role (e.g. Project Owner renewing Unit Personnel)
- `500 Internal Server Error`
  - User / Project Key errors (any)

---

## `s3.py`

### S3Info

- [Authentication errors](#authentication)
- `400 Bad Request`
  - Decorators
    - Validation error
  - Schemas
    - Project does not exist
  - Project is not 'In Progress'
- `403 Forbidden`
  - Schemas
    - User does not have access to project
- `500 Internal Server Error`
  - Database errors
  - S3 connection errors

---

## `superadmin_only.py`

### AllUnits

- [Authentication errors](#authentication)
- `500 Internal Server Error`
  - Decorators
    - Database errors

### MOTD

- [Authentication errors](#authentication)
- `400 Bad Request`
  - Decorators
    - Json required but not provided
  - No Message Of The Day provided
- `500 Internal Server Error`
  - Decorators
    - Database errors

---

## `user.py`

### AddUser

- [Authentication errors](#authentication)
- `400 Bad Request`
  - Decorators
    - Validation error
    - Json required but not provided
  - Schemas
    - Project does not exist
  - Invalid user role for user being invited
  - No email specified for invited user
  - Existing user but no project provided
  - Attempting to invite user to project but no project ID provided
  - Attempting to add Super Admin to project
  - A Super Admin is attempting to invite a 'Unit Personnel' or 'Unit Admin' to an non-existent unit
  - A Super Admin is attempting to invite a 'Unit Personnel' or 'Unit Admin' but a unit public ID is not provided
  - The invite did not succeed
- `403 Forbidden`
  - Schemas
    - User does not have access to project
  - Trying to add any user as a 'Unit Admin', 'Unit Personnel' or 'Super Admin' to a project
  - Trying to add an existing user with the role 'Unit Admin', 'Unit Personnel' or 'Super Admin' to a project
  - Attempting to change a users project role to existing role
  - User-specific project key not found: user does not have access
  - Attempting to invite a role higher in the 'hierarchy' (e.g. Unit Admin attempting to invite a Super Admin)
- `500 Internal Server Error`
  - Database errors
  - User / Project Key errors (any)

_The following is **per user**, not the status code returned to the CLI_

- `400 Bad Request`
  - Trying to invite Project Owner but no project provided
  - Trying to invite _as_ Project Owner but no project provided
  - Super Admin attempting to invite user to project
- `403 Forbidden`
  - Inviting a role outside of permissions (e.g. Researcher inviting Unit Personnel)

### RetrieveUserInfo

- [Authentication errors](#authentication)

### DeleteUserSelf

- [Authentication errors](#authentication)
- `403 Forbidden`
  - Not enough existing Unit Admins
- `500 Internal Server Error`
  - Database errors

### UserActivation

- [Authentication errors](#authentication)
- `400 Bad Request`
  - Decorators
    - Validation error
    - Json required but not provided
  - An email is not provided
  - Attempting to activate/deactivate a non-existent user
  - An action (activate/deactivate) was not provided
  - Attempting to activate account which is already active
  - Attempting to deactivate account which is already deactivated
- `403 Forbidden`
  - A 'Unit Admin' is attempting to activate/deactivate a Researcher or Super Admin
  - Attempting to activate/deactivate a 'Unit Admin' or 'Unit Personnel' outside of the own unit
  - Attempting to activate/deactivate own account
- `500 Internal Server Error`
  - Database errors
  - User / Project Key errors (any)

### DeleteUser

- [Authentication errors](#authentication)
- `400 Bad Request`
  - Decorators
    - Validation error
  - Attempting to delete a non existent user
  - Attempting to delete 'Unit Personnel' or 'Unit Admin' outside of own unit
  - A 'Unit Admin'/'Unit Personnel' attempting to delete a 'Researcher' or a 'Super Admin'
  - Attempting to delete own account (DeleteUserSelf used for this)
- `403 Forbidden`
  - User does not have permission to delete an invite
- `500 Internal Server Error`
  - Database errors

### RemoveUserAssociation

- [Authentication errors](#authentication)
- `400 Bad Request`
  - Decorators
    - Validation error
    - Json required but not provided
  - Schemas
    - Project does not exist
  - Attempting to remove users project access but no user email provided
  - User not found in database
  - User does not have access to project
- `403 Forbidden`
  - Schemas
    - User does not have access to project
- `500 Internal Server Error`
  - Database errors

### EncryptedToken

- [Authentication errors](#authentication)
- `429 Too Many Requests`
  - Attempting to authenticate too many times within an hour
- `500 Internal Server Error`
  - User / Project Key errors (any)

### SecondFactor

- [Authentication errors](#authentication)
- `400 Bad Request`
  - Decorators
    - Validation error
- `401 Unauthorized`
  - Invalid or expired token

### ShowUsage

- [Authentication errors](#authentication)
- `403 Forbidden`
  - Attempting to get usage information as Researcher or Super Admin
- `500 Internal Server Error`
  - Database errors

### Users

- [Authentication errors](#authentication)
- `400 Bad Request`
  - Decorators
    - Database errors
  - A Super Admin is attempting to list the unit users but no unit public ID is specified
  - A Super Admin is attempting to list the unit users but the unit public ID is invalid - no unit with that ID
