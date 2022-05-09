# Endpoints and their status code reponses

## Authentication

- Incorrect username or password: `401 Unauthorized`
- Expired token: `401 Unauthorized`
- Invalid token: `401 Unauthorized`
- Incorrect role: `401 Unauthorized`
- Password reset after last authenticated token generated: `401 Unauthorized`
- Two Factor Authentication not provided: `401 Unauthorized`
- User is deactivated: `403 Forbidden`

## Decorators 

- Json required but not provided: `400 Bad Request`
- Validation error: `400 Bad Request`

## `project.py`

### CreateProject

- Missing required info or wrong format: `400 Bad Request`
- Less than 2 Unit Admins: `403 Forbidden`
- User / Project Key errors (any): `500 Internal Server Error`
- Database errors: `500 Internal Server Error`
- S3 connection errors: `500 Internal Server Error`
- No user invites sent: `400 Bad Request`
- [AddUser errors](#adduser)

## `user.py`

### AddUser

_In Progress_
