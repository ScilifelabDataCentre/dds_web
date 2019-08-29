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
```
curl -X PUT http://delport:delport@127.0.0.1:5990/projects
curl -X PUT http://delport:delport@127.0.0.1:5990/dp_users
```
2.
```
curl -d @projects.json -H "Content-type: application/json" -X POST http://delport:delport@127.0.0.1:5990/projects/_bulk_docs
curl -d @dp_users.json -H "Content-type: application/json" -X POST http://delport:delport@127.0.0.1:5990/dp_users/_bulk_docs
```
