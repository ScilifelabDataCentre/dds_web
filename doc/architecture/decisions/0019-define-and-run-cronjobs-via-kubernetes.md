# 19. Define and run cronjobs via Kubernetes

Date: 2023-01-19

## Status

Accepted

## Context

Prior to this decision, the DDS has defined the cronjobs in a module within the app, and they have been run via Flask-APScheduler. This worked without any issues for a while, but when the deployment setup on the cluster changed we started getting errors during for example the project status transitions which are run every day at midnight. After some investigating we noticed that the issues are due to the DDS running on two pods, with two threads each, leading to multiple executions of the same cronjobs simultaneously. I order to avoid these issues now and in the future, we are now defining the current cronjobs as Flask commands and setting up the cronjobs in k8s.

## Decision

Change the current cronjobs to Flask commands. Set up k8s cronjobs to run the Flask commands. All future cronjobs should be configured in this way; There should be no cronjobs defined within the DDS app.

## Consequences

The cronjobs defined in k8s will start up a new pod at a certain time, run the specific command, and then shut down the pod. Therefore there will be more than 2 pods whenever a cronjob is run, and each cronjob will only be executed once, resulting in the avoidance of the deadlocks and duplicate errors that we are currently experiencing.
