# 18. React as JavaScript framework for frontend

Date: 2022-05-05

## Status

Accepted

## Context

When the development of the DDS began in 2019, the CLI and web/API development proceeded in parallel. Since Flask was chosen as the Python backend regarding the API, it was also used for rendering HTML for the frontend. As the development has proceeded, there have been several major discussions regarding whether or not the DDS framework should use Flask to render HTML, or if we should switch to a JavaScript framework. Since the web contained a lot of code duplication from the CLI and was also overly complicated, it was decided by the Product Owner that we should remove the web frontend and begin from scratch and at that time decide on whether or not Flask or a JS framework should be used. This decision was however postponed for the time being since there was no time, the focus needed to be on getting the DDS into production before the end of March, and that the team did not have enough time, knowledge or previous experience to proceede with the web development or learn a new framework. Currently, a part of the web interface is reintroduced, for the functionalities that are vital for the DDS functionality. However, since the DDS has now had its first release, the next step is to create an easy interface. There are also enough full time team members and there is more time. 

* important aspect: enough in the DC that know it, there's a community to get help

* alternatives: Angular, React, VueJS

## Decision

It was decided within the DDS team that we should switch from Flask+HTML for the frontend to the JavaScript framework ReactJS. 

## Consequences

* majority of team members have no experience with it
* At least one frontend developer outside of DDS team have experience with it
* 

What becomes easier or more difficult to do and any risks introduced by the change that will need to be mitigated.
