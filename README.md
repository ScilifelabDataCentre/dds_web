# delivery_portal
An open source data delivery portal for Scilifelab facilities

**WIP at the moment**

## Setup (quick development mode): 
1. Install Docker if you don't already have it. 
Mac: `https://docs.docker.com/v17.12/docker-for-mac/install/`
Ubuntu: `https://www.digitalocean.com/community/tutorials/how-to-install-and-use-docker-on-ubuntu-18-04?fbclid=IwAR3zNawDfhtWhehs4pbUIbHSxwqiVnLRafq2gY6rLSZVY_F0b81b7MHiTQ0`
2. 
```cp dportal.yaml.sample dportal.yaml
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
curl -d @dbfiles/projects.json -H "Content-type: application/json" -X POST http://delport:delport@127.0.0.1:5984/projects/_bulk_docs
curl -d @dbfiles/dp_users.json -H "Content-type: application/json" -X POST http://delport:delport@127.0.0.1:5984/dp_users/_bulk_docs
```
