# Endpoints and their status code reponses

## `project.py`

### CreateProject

Auth - should be moved later 
- Incorrect username or password: `401 Unauthorized`
- Expired token: `401 Unauthorized`
- Invalid token: `401 Unauthorized`
- Incorrect role: `401 Unauthorized`
- Password reset after last authenticated token generated: `401 Unauthorized`
- Two Factor Authentication not provided: `401 Unauthorized`
- User is deactivated: `403 Forbidden`
