<<<<<<< HEAD
# Data Delivery Portal -- **WIP**
A a single cloud-based system for all SciLifeLab facilities, where data generated throughout each project can be delivered to the research groups in a fast, secure and simple way. 
=======
# Data Delivery Portal 
An open source data delivery system for Scilifelab facilities
>>>>>>> b9190ec48aca4403b59aa1a6fc8ecf63ff27af3c

The Delivery Portal consists of two components:
* The **web interface** where the research groups and facilities will be able to follow the data
delivery progress. The web interface will also be an option for the delivery within small
projects, e.g. small and/or few files.
* The **command line interface (CLI)**. This will be used for data delivery within larger projects
and/or projects resulting in the production of large amounts of data, e.g. sequence data.

---
## Setup docker environment:

**1. Docker installation**

	Mac:  
	https://docs.docker.com/v17.12/docker-for-mac/install

	Ubuntu:  
	https://docs.docker.com/install/linux/docker-ce/ubuntu/

**2. In _S3-Upload-Proxy_ folder** 
* Go to subfolder: `cd dev_utils`
* Comment out _s3_proxy_ part in docker-compose.yml file 
* Build and start service: `docker-compose up -d` 
* Back to S3-Upload-Proxy folder: `cd ..`
* Start the s3-proxy: `SERVER_CONFILE=dev_utils/config.yaml go run .`
* Go to https://localhost:9000/ and log in with ElexirID and 987654321
* Create a `test` bucket and an inner "bucket" called some username --> 
	```s3://test/<username>``` 

**3. In _dp_api_ folder**
* Setup CLI: `pip3 install --editable .`

**4. In root (Data-Delivery-Portal)** 
* Build and run containers

	```bash
	cp dportal.yaml.sample dportal.yamp
	docker-comopose up
	```

	* To use terminal after starting services, use the `-d` option.

		```
		cp dportal.yaml.sample dportal.yaml
		docker-compose up -d 
		```

	* To stop service: 
		```bash 
		docker-compose down
		```
**5. Setup database**
* Go to http://localhost:5984/_utils/#setup 
* Create the databases. 
	```bash
	curl -X PUT http://delport:delport@127.0.0.1:5984/project_db
	curl -X PUT http://delport:delport@127.0.0.1:5984/user_db
	```
* Import the database contents. 
	```bash
	curl -d @dbfiles/project_db.json -H "Content-type: application/json" -X POST http://delport:delport@127.0.0.1:5984/project_db/_bulk_docs
	curl -d @dbfiles/user_db.json -H "Content-type: application/json" -X POST http://delport:delport@127.0.0.1:5984/user_db/_bulk_docs
	```
