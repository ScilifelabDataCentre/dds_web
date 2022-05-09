# Endpoints and their status code reponses

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

## Utils

- `400 Bad Request`
    - Invalid email type

## `project.py`

### CreateProject

- [Authentication errors](#authentication)
- [AddUser errors](#adduser)
- `400 Bad Request`
    - Decorators
        - Json required but not provided: 
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

### GetPublic

- [Authentication errors](#authentication)
- Decorators
  - Validation error: `400 Bad Request`
- Schemas
  - Project does not exist: `400 Bad Request`
  - User does not have access to project: `403 Forbidden`
- No public key found for project: `500 Internal Server Error`

### GetPrivate

- [Authentication errors](#authentication)
- Decorators
  - Validation error: `400 Bad Request`
- Schemas
  - Project does not exist: `400 Bad Request`
  - User does not have access to project: `403 Forbidden`
- User / Project Key errors (any): `500 Internal Server Error`

### UserProjects

- [Authentication errors](#authentication)
- Database errors: `500 Internal Server Error`

### RemoveContents

- [Authentication errors](#authentication)
- Decorators
  - Database errors: `500 Internal Server Error`
  - Validation error: `400 Bad Request`
- Schemas
  - Project does not exist: `400 Bad Request`
  - User does not have access to project: `403 Forbidden`
- Incorrect status: `400 Bad Request`
- Nothing to delete in project: `400 Bad Request`
- Database or S3 issues: `500 Internal Server Error`

### ProjectUsers

- [Authentication errors](#authentication)
- Decorators
  - Validation error: `400 Bad Request`
- Schemas
  - Project does not exist: `400 Bad Request`
  - User does not have access to project: `403 Forbidden`

### ProjectAccess

- [Authentication errors](#authentication)
- Decorators
  - Validation error: `400 Bad Request`
  - Json required but not provided: `400 Bad Request`
  - Validation error: `400 Bad Request`
- Required email adress missing: `400 Bad Request`
- User getting access does not exist: `400 Bad Request`
- Schemas
  - Project does not exist: `400 Bad Request`
  - User does not have access to project: `403 Forbidden`
- Attempting to renew your own project access: `403 Forbidden`
- Attempting to renew access for invalid role (e.g. Project Owner renewing Unit Personnel): `403 Forbidden`
- User / Project Key errors (any): `500 Internal Server Error`

## `user.py`

### AddUser

_In Progress_

_The following is **per user**, not the status code returned to the CLI_

- Trying to invite Project Owner but no project provided: `400 Bad Request`
- Trying to invite _as_ Project Owner but no project provided: `400 Bad Request`
- Super Admin attempting to invite user to project: `400 Bad Request`
- Inviting a role outside of permissions (e.g. Researcher inviting Unit Personnel): `403 Forbidden`
