# Endpoints and their status code reponses

## Authentication

- Incorrect username or password: `401 Unauthorized`
- Expired token: `401 Unauthorized`
- Invalid token: `401 Unauthorized`
- Incorrect role: `401 Unauthorized`
- Password reset after last authenticated token generated: `401 Unauthorized`
- Two Factor Authentication not provided: `401 Unauthorized`
- User is deactivated: `403 Forbidden`

## Utils

- Invalid email type: `400 Bad Request`

## `project.py`

### CreateProject

- [Authentication errors](#authentication)
- Decorators
    - Json required but not provided: `400 Bad Request`
    - Validation error: `400 Bad Request`
- Missing required info or wrong format: `400 Bad Request`
- Less than 2 Unit Admins: `403 Forbidden`
- User / Project Key errors (any): `500 Internal Server Error`
- Database errors: `500 Internal Server Error`
- S3 connection errors: `500 Internal Server Error`
- No user invites sent: `400 Bad Request`
- [AddUser errors](#adduser)

### ProjectStatus

#### `get`

- [Authentication errors](#authentication)
- Decorators
    - Validation error: `400 Bad Request`
- Schemas
    - Project does not exist: `400 Bad Request`
    - User does not have access to project: `403 Forbidden`

#### `post`

- [Authentication errors](#authentication)
- Decorators
    - Json required but not provided: `400 Bad Request`
    - Validation error: `400 Bad Request`
- Schemas
    - Project does not exist: `400 Bad Request`
    - User does not have access to project: `403 Forbidden`
- Missing required status info: `400 Bad Request`
- Invalid new status: `400 Bad Request`
- Database errors: `500 Internal Server Error`
- Invalid status transition: `400 Bad Request`
- `release_project`
    - Invalid deadline: `400 Bad Request`
    - Max number of times available reached: `400 Bad Request`
- `expire_project`
    - Invalid deadline: `400 Bad Request`
- `delete_project`
    - Trying to delete project which has been availble: `400 Bad Request`
    - Database or S3 issues: `500 Internal Server Error`
- `archive_project`
    - Trying to archive a project which has been previously made available: `400 Bad Request`
    - Database or S3 issues: `500 Internal Server Error`

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

- 
## `user.py`

### AddUser

_In Progress_

_The following is **per user**, not the status code returned to the CLI_

- Trying to invite Project Owner but no project provided: `400 Bad Request`
- Trying to invite _as_ Project Owner but no project provided: `400 Bad Request`
- Super Admin attempting to invite user to project: `400 Bad Request`
- Inviting a role outside of permissions (e.g. Researcher inviting Unit Personnel): `403 Forbidden`

