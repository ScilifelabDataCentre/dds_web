# delivery_portal
An open source data delivery portal for Scilifelab facilities

**WIP at the moment**


## Quick development mode:
```
cp dportal.yaml.sample dportal.yaml
docker-compose up
```

## Database setup:
1. 
The db needs setup: `http://localhost:5984/_utils/#setup`

2.
```
curl -X PUT http://delport:delport@127.0.0.1:5984/projects
curl -X PUT http://delport:delport@127.0.0.1:5984/dp_users
```
3.
```
curl -d @projects.json -H "Content-type: application/json" -X POST http://delport:delport@127.0.0.1:5984/projects/_bulk_docs
curl -d @dp_users.json -H "Content-type: application/json" -X POST http://delport:delport@127.0.0.1:5984/dp_users/_bulk_docs
```
