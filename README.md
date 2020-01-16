# delivery_portal
An open source data delivery portal for Scilifelab facilities

**WIP**

---
## Setup docker environment:

1. Install Docker if you don't already have it.

Mac:  
https://docs.docker.com/v17.12/docker-for-mac/install

Ubuntu:  
https://docs.docker.com/install/linux/docker-ce/ubuntu/

2. Build and run containers

```bash
cp dportal.yaml.sample dportal.yaml
docker-compose up
```

**To use terminal after starting services, use the `-d` option.**
```bash 
cp dportal.yaml.sample dportal.yaml
docker-compose up -d 
```

**To stop service** (if `-d` option used or in new terminal tab):
```bash 
docker-compose down
```

## Database setup:

### 1. Setup database. Go to: 

http://localhost:5984/_utils/#setup

### 2. Create the databases. 

```bash
curl -X PUT http://delport:delport@127.0.0.1:5984/projects
curl -X PUT http://delport:delport@127.0.0.1:5984/users
```

### 3. Import the database contents. 

```bash
curl -d @dbfiles/project_db.json -H "Content-type: application/json" -X POST http://delport:delport@127.0.0.1:5984/projects/_bulk_docs
curl -d @dbfiles/user_db.json -H "Content-type: application/json" -X POST http://delport:delport@127.0.0.1:5984/users/_bulk_docs
```
