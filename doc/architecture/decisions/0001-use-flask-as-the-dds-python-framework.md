# 1. Use Flask as the DDS Python framework

Date: 2019 / 2020

## Status

Accepted

## Context

In the beginning of development the Python web framework Tornado was used, mainly due to it being used within other applications developed by the SciLifeLab Data Centre. However, it was later investigated whether Tornado was the best choice of framework for the Data Delivery System. The final choice was between Tornado and the microframework Flask.

### Advantages

| Flask                                                      | Tornado                                                       |
| ---------------------------------------------------------- | ------------------------------------------------------------- |
| Plenty of online resources                                 | Asynchronous - can handle thousands of concurrent connections |
| Flexible                                                   | Flexible                                                      |
| Simple                                                     | Fast                                                          |
| REST Support via extensions                                | Simple                                                        |
| Integrated testing system - improved stability and quality | Built-in support for user authentication                      |

### Disadvantages

| Flask                                                       | Tornado                          |
| ----------------------------------------------------------- | -------------------------------- |
| No built-in support for user authentication (-> extensions) | Not as many online resources     |
| Efficiency can be affected by extensions                    | No built-in support for REST API |

## Decision

We will use Flask as the framework for the DDS.

## Consequences

Flask is flexible and simple, extensions provide a large variety of functionalities including REST API support, it has an integrated testing system and there is more online support than for Tornado. The built-in asynchronicity in Tornado is not an important feature since the system will not be used by thousands of users at a given time.

## References

[Python’s Frameworks Comparison: Django, Pyramid, Flask, Sanic, Tornado, BottlePy and More](https://www.netguru.com/blog/python-frameworks-comparison)
