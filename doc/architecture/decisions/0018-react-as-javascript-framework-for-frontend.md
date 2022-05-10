# 18. React as JavaScript framework for frontend

Date: 2022-05-05

## Status

Accepted

## Context

When the development of the DDS began in 2019, the CLI and web/API development proceeded in parallel. Since Flask was chosen as the Python backend (the API), it was also used for rendering HTML for the frontend. As the development has proceeded, there have been several major discussions regarding whether or not the DDS framework should use Flask to render HTML, or if we should switch to a JavaScript framework. Since the web contained a lot of code duplication from the CLI and in addition was overly complicated, it was decided by the Product Owner that we should remove the web frontend and begin from scratch and at that time decide on whether or not Flask or a JS framework should be used. This decision was however postponed for the time being since the focus needed to be on getting the DDS into production before the end of March 2022, and that the team did not have enough time, knowledge or previous experience to proceede with the web development or learn a new framework. Currently, a part of the web interface is reintroduced, for the functionalities that are vital for the DDS functionality. However, since the DDS has now had its first release, the next step is to create an easy interface. There are also enough full time team members and there is more time. 

One of the most important aspects to consider when deciding on how the frontend should be built is that there need to be enough members of the Data Centre development team that know the framework or have worked with something very similar and therefor can easily get into it quickly. Another aspect is the need for a large community and available resources such as documentation. Due to these points, the JavaScript frameworks Angular, React and VueJS were chosen as alternatives to Flask.

The JS frameworks would mean a switch to the JAM (JavaScript, API and Markup) Technology Stack - web applicatons built with _JavaScript_ to fetch data from an _API_ and presenting it with _Markup_. JAM is only frontend and would replace the templates currently used by Flask. 

Alternatives for frontend:
* Flask: Not JAM, but would be Python and all team members know it.  
* Angular: Has a steeper learning curve compared to the others, and almost noone within the Data Centre development team has experience with it. 
* React: Slightly steeper learning curve than VueJS (but not much), large community and at least two within the Data Centre development team is familiar with it. 
* VueJS: "Developer-friendly" documentation and easier to learn than the others. May also be a better fit for smaller projects but there seems to be a discussion about that. At least two within the Data Centre development team is familiar with it. 

## Decision

It was decided within the DDS team that we should switch from Flask+HTML for the frontend to the JavaScript framework **ReactJS**. 

## Consequences

### Consequences of switching to JAM

#### Advantages

* More flexibility with functionality - possible to group functionality into components
* Allows reuse of components
* Allows for easier testing since we can test each component separately

#### Disadvantages 

* Requires JavaScript
    * Latency increases when there are a lot of TCP requests being made
    * Older web browsers and web browsers that do not have suppose for JavaScript are not supported
* The code could get complex
* Computation intensive code may block the thread, since JavaScript is single-threaded
* Learning curve

### Additional consequences

The switch to ReactJS means that we need to swap out the current frontend completely. This will take time. It will also take time to learn it. However, one team member has experience as a frontend developer and is familiar with ReactJS. If we were to get stuck, we can ask the other frontend developer within Data Centre for help, and there's a large community online which will be of help. 
