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

***

## Utils

- `400 Bad Request`
  - Invalid email type

***

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

***

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

***

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
    - Validation error:
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

***

## `user.py`

### AddUser

_In Progress_

_The following is **per user**, not the status code returned to the CLI_

- `400 Bad Request`
  - Trying to invite Project Owner but no project provided
  - Trying to invite _as_ Project Owner but no project provided
  - Super Admin attempting to invite user to project
- `403 Forbidden`
  - Inviting a role outside of permissions (e.g. Researcher inviting Unit Personnel)
