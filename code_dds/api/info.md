# Request methods
| Method | Purpose | HTTP response |
|--------|:-------:|:--------------:|
| GET | Obtain resource or collection of resources | 200 |
| POST | Create new resource and add to collection. <br> Server chooses URL of new resource. <br> Returns it in a Location header in response. | 201 |
| PUT | Modidy an existing resource or create new <br> when client can choose resource URL | 200 or 204 | 
| DELETE | Delete a resource or collection of resources | 200 or 204 |


When method not supported for a given resource -> response 405 status code (_Method not allowed_). 
