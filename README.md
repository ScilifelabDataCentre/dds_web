# delivery_portal
An open source data delivery portal for Scilifelab facilities

**WIP at the moment**


## Quick development mode:
```
cp dportal.yaml.sample dportal.yaml
docker-compose up
```

## Database setup:
<<<<<<< HEAD
1.
=======
1. 
>>>>>>> 745f781ab5aa457902bcf6a2f54d2f3475a8673e
The db needs setup: `http://localhost:5984/_utils/#setup`

2.
```
curl -X PUT http://delport:delport@127.0.0.1:5984/projects
curl -X PUT http://delport:delport@127.0.0.1:5984/dp_users
```
3.
```
curl -d @dbfiles/projects.json -H "Content-type: application/json" -X POST http://delport:delport@127.0.0.1:5984/projects/_bulk_docs
curl -d @dbfiles/dp_users.json -H "Content-type: application/json" -X POST http://delport:delport@127.0.0.1:5984/dp_users/_bulk_docs
```
