# delivery_portal
An open source data delivery portal for Scilifelab facilities

**WIP at the moment**

## Setup docker environment:

1. Install Docker if you don't already have it.

Mac: `https://docs.docker.com/v17.12/docker-for-mac/install/`

Ubuntu: `https://www.digitalocean.com/community/tutorials/how-to-install-and-use-docker-on-ubuntu-18-04?fbclid=IwAR3zNawDfhtWhehs4pbUIbHSxwqiVnLRafq2gY6rLSZVY_F0b81b7MHiTQ0`

2. Run the command.
```
cp dportal.yaml.sample dportal.yaml
docker-compose up
```

## Database setup:
### 1. Setup database. Go to: 
`http://localhost:5984/_utils/#setup`

### 2. Create the _projects_ and _dp_users_ databases. 
```bash
curl -X PUT http://delport:delport@127.0.0.1:5984/projects
curl -X PUT http://delport:delport@127.0.0.1:5984/dp_users
```

### 3. Import the database contents. 
```bash
curl -d @dbfiles/projects.json -H "Content-type: application/json" -X POST http://delport:delport@127.0.0.1:5984/projects/_bulk_docs
curl -d @dbfiles/dp_users.json -H "Content-type: application/json" -X POST http://delport:delport@127.0.0.1:5984/dp_users/_bulk_docs
```

## CLI use (in `cli_api` folder)
```bash
python3 dp_cli.py --file [files-to-upload]
```
