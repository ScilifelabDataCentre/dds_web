# 21. Plan for 2024: Objectives and Key Results

Date: 2023-10-16

## Status

Accepted

## Context

The Product Owner (PO) / Project Leader (PL) of Team Hermes - responsible for the development and maintenance of the Data Delivery System (DDS) - is going on parental leave from November 17th 2023. Due do this, and that the substitute(s) / replacement(s) has not had enough time to learn the system in order to fully take over the PO / PL responsibilities, there needs to be a plan for what the team should work on during the coming year. Starting a more formal plan for the coming year (now and in the future) is also a general improvement to the team and stakeholders, since it will allow for more tranparency outward and help guide the team's focus.

In order to plan for the coming year (2024, and December 2023), the team is using the tool / method _OKRs: Objects and Key Results_.

> OKR [is] a collaborative goal-setting methodology used by teams and individuals to set challenging, ambitious goals with measurable results.
>
> -- <cite>[What Matters](https://www.whatmatters.com/faqs/okr-meaning-definition-example)</cite>

> An **Objective** is what you want to accomplish.
> [Should be]:
>
> - Significant
> - Concrete
> - Action-oriented
> - Inspirational
>
> Can be set annually or over [a] [...] longer term.
>
> **Key Results** are how you will accomplish the _Objectives_.
> [Should be]:
>
> - Specific
> - Timebound
> - Aggressive yet realistic
> - Measurable
> - Verifiable
>
> Can be set quarterly and evolve as work progresses.
>
> -- <cite>[What Matters](https://www.whatmatters.com/faqs/okr-meaning-definition-example)</cite>
>
> Initiatives [are] tasks [that are] required to drive [the] progress of key results.
>
> -- <cite>[Intuit Mint](https://mint.intuit.com/blog/planning-2/okr-framework/)</cite>

### Discussions regarding possible objectives

#### Possible objective: "Improve user experience via UI"

##### Alternative 1: Implement the `dds-cli` functionality in the web interface.

- The web interface will not be a good way for uploads and downloads of huge amounts of data. The units are also saying this.
- Implementing the functionality in the web interface would require us to have a front-end developer that also has experience in cryptography. We (the PO mainly) have been asking- and waiting for this person for a long time, so we cannot expect that that's going to happen any time soon. The last time it was mentioned was both before and after summer 2023; since then we haven't heard or said anything regarding this. Therefore, creating the web interface that is envisioned - a complete reset of the web using some JS framework - is not possible.
  - Even if a front-end developer was to get hired at some point during 2024, doing a complete reset of the frontend (which houses functionality required to register, reset password, setup 2FA, etc) and building the web from scratch, while the person who has been involved in developing the majority of the code, is away, is **not** a good idea.
- If we were to work on implementing the functionality into the web interface as it is now, without having a front-end developer, we would have to continue using pure flask in the web, and that would mean that we would need to make a duplicate of practically all of the API code that exists, because:
  - Calling the API endpoints from the Flask routes does not work since those endpoints require authentication tokens - the ones that the CLI uses.
  - Moving the API code, creating helper functions, and changing everything in order to use the new helper functions in both the API and web should not be done when the PO is away; It's too much work and it risks the functionality in the web. We should be adding functionality to the system during 2024, **not** refactoring and risking working functionality to break.
- Duplicating the code for listing projects, users, files, adding users to projects (etc, etc) in the web means that we later on will have to redo it all and the team will have spent time on something that will not be used anyway since the upload and download by pure flask and html is not a good idea (and not possible with huge files due to load on cluster). Also, upload and download of potentially huge amounts of data via browser is as mentioned above not a good solution.

**Because of these items, implementing the functionality in the web interface is not an option; we won't plan for working on the web interface during the coming year.**

##### Alternative 2: Creating a Graphical User Interface (GUI)

- The unit's _end-users_ (the users downloading the data) would benefit from this.
- The NGI units that do not need the download functionality for their end users in the GUI also do not need it in the web, they just have bioinformaticians that help the users and the bioinformaticians are familiar with terminal tools
- Other smaller units have less experienced end users and are more likely to want to download locally and to want to click buttons instead of using the terminal
- This GUI would be very simple to begin with, it could (for example) be created by `tkinter` or another simple package (google "simple GUI python" or similar, there are several). The main thing here is that we **should not need to write new code for the actual DDS functionality**; The idea is that the GUI would run the CLI commands when buttons are clicked etc. Buttons would run the commands, and the same things that are displayed in the CLI would be displayed in the GUI.
  - We could start with the authentication, listing of the projects, their deadlines etc, users, project users, inviting users etc.
  - The GUI would automatically use the authentication token.
  - We could technically implement download, but we could start with displaying the commands and allow them to copy paste the commands to the terminal
  - The very simple GUI can be compiled with the pyinstaller package via GitHub actions, in a similar way that the CLI is currently. The user would then download the GUI, open it and then do what they want in a simple way.
- This would therefore mean that we wouldn't duplicate code, we would just use the code that already exist.
- The GUI would not be able to use on HPC clusters etc _but neither would the browser_.
- Both options would currently download to the local computer.
- Both the GUI and the web interface would later maybe be able to pipe the data to a long term storage location instead of downloading locally, but the plans for how that would work exactly are not made yet, and GUI or web interface shouldn't make a difference since the functionality will anyway likely be managed and executed via the API.
- Making the GUI is still not a simple task, we would still need to make reasonable plans and not go overboard. We would start small, let the users try it out or have demos, and if this is not something that would be used, you would scrap the GUI plan and move on to a new idea or a new objective.

**So the choices we have are:**

1. Start making a GUI **OR...**
2. Come up with a new objective.

## Decision

The sections below have the following structure:

> **Objective X: [short title] -- [long description]**
>
> - **Key Result Y for Objective X [COMMITTED / ASPIRATIONAL / LEARNING]:** [Description / goal]
>   - Initiative 1
>     - _Notes or possible task example_
>   - Initiative 2
>   - _etc..._

> **The objectives, key results and initiatives are also available for the team on Confluence: https://scilifelab.atlassian.net/wiki/spaces/deliveryportal/pages/2615705604/Plan+for+2024**

> The initiatives have been added to the [Jira Board](https://scilifelab.atlassian.net/jira/software/projects/DDS/boards/13/backlog?epics=visible) as _epics_. Tasks that fall under the initiatives should therefore be marked as a part of those epics. This can be changed if the team wants to try another structure.

### Objective 1: Support -- "Optimize support"

- **Workshop for users [COMMITTED]:** Plan for a workshop for DDS users, intended to present the system, help users get started and answer common questions. The workshop should be run at least once a year.
  - Schedule the workshop for autumn 2024, before summer 2024.
    - _Talk to training hub to plan for event._
  - Create workshop material before the workshop (autumn 2024)
    - _Decide on target audience_
    - _List parts to include in workshop, depending on audience_
    - _Create workshop content_
  - Improve workshop material based on audience feedback by the end of 2024
    - _Collect feedback within 2 weeks after the workshop_
- **Support documentation [COMMITTED]:** Create or update support documentation for the top 5 most common support inquiries to facilitate self-service
  - Identify the top 5 most common support inquiries by [??]
    - _List top 5 most common support inquiries send to Data Centre_
    - _Ask Units (production) what the 5 most common support inquiries they get from their users_
    - _Ask Units (production) about what 5 things they think should be clarified_
    - _Ask Units (testing) about what 5 things they think should be clarified_
  - Analyse the support inquiries and feedback by ??
    - _Group the support inquiries into "themes"_
    - _Choose the 5 most common inquiries_
    - _Investigate which of the inquiries need to have their documentation updated / created_
  - Create / update the documentation for the 5 most common support inquiries by ??
    - _Inquiry 1_
    - _Inquiry 2…_
  - Get feedback/review of documentation from ?? (outside team)
- **Ticket Volume [ASPIRATIONAL]:** Reduce the number of "unnecessary" support tickets submitted by 50% percent within the next 6 months months, by implementing a chatbot in the web interface.
  "Unnecessary": questions that should go to units or that units should already know.
  - Identify number of unnecessary support tickets in the last x months
    - _Find 3 possible tools for creating the chatbot_
    - _List pros and cons for the possible tools_
    - _Make decision_
  - Decide on design and architecture of Chatbot by ??
  - Create a Chatbot prototype by ?? that can answer questions regarding where the documentation and technical overview is located and who they should contact in the case of a question that the bot cannot answer
  - Implement "was this helpful?" in the chatbot by ??
  - Implement responses to top 10 most common irrelevant questions by ??
  - Find a way to evaluate the chatbot

### Objective 2: Quality -- "Improve software quality"

- **Resolve security alerts [ASPIRATIONAL]:** Resolve all solvable (with known fixes) critical security alerts within 7 days, high-severity alerts within 14 days and medium-severity alerts within a month.
  - Find a way to implement a routine on the scrum cycle
  - Evaluate if different notification/alerts systems outside GitHub could also be helpful
  - Decide a new release procedure for critical alerts when there is no schedule release soon
    - _Study how feasible is to redeploy more often_
    - _Study if there is a way, and if so, how to redeploy backend (rolling updates) in Kubernetes_
- **Test coverage [ASPIRATIONAL]:** Increase test coverage for dds_web to 100% and dds_cli to 70%.
  - Increase the coverage for the 10 files within dds_web with the least amount of coverage to above 90% by ??
    - _List 10 files with the least amount of coverage_
    - _Increase coverage for file 1_
    - _Increase coverage for file 2... etc_
  - Increase the coverage for the 10 files within dds_cli with the least amount of coverage to above 40% by ??
    - _List 10 files with the least amount of coverage_
    - _Increase coverage for file 1_
    - _Increase coverage for file 2... etc_
  - Add tests for all changes in the dds_cli code, aiming at at least 50% coverage. The tests should be added prior to merging the code.
  - For all changes in the dds_web code, add tests so that the coverage is 100%. The tests should be added prior to merging the code.
- **API documentation [COMMITTED]:** Create / Generate documentation for the dds_web/api, which covers all endpoints.
  - Decide on a tool for generating the API documentation
    - _Find 3 possible solutions / tools_
    - _List pros and cons for the possible tools/solutions_
    - _Make decision_
  - Research if it is possible to automate the documentation generation when a new endpoint is added
    - _Maybe GitHub Actions_
    - _Maybe the tool used allows for that_
  - Make API documentation accessible first for the team members, then discuss if we should publish for everyone

### Objective 3: GUI -- "Improve user experience via a GUI prototype"

- **Reduced learning curve [ASPIRATIONAL]:** Users can perform common tasks in the new GUI in less time and effort compared to the CLI.
  - Make a list of the 5 most used features that could be simplified via the GUI
  - Design the layout of those features
  - Implement the GUI so it is easily accessible for users
    - _Decide a framework/technology that can be easily ported to different OS architectures_
    - _Find 3 possible tools/solutions for creating the GUI_
    - _List pros and cons for the possible tools/solutions_
    - _Make decision_
  - Ask for feedback from someone that is using the CLI atm
- **Cross-Platform Consistency [COMMITTED]:** Ensure the GUI functions consistently and seamlessly on macOS (latest), Linux (ubuntu) and Windows (latest).
  - Research best way to publish the binaries to the users
  - Create a GitHub action for generating the GUI binary for macOS lastest
  - Create a GitHub action for generating the GUI binary for ubuntu latest
  - Create a GitHub action for generating the GUI binary for windows latest
  - Continuously test all implemented features for cross-platform consistency.
    - _Discuss if we should focus more on some OS over others because of:_
      1. macOS (team develops on mac)
      2. Windows (most users that need the GUI)
      3. Linux (would usually be more comfortable with command line)
- **Feedback [LEARNING]:** Get feedback on GUI prototype from 5 users on each OS.
  - Identify users: Make list of 20 people to ask for feedback from
  - Create testing protocol, covering the testing of all features implemented in the GUI prototype
  - Gather, analyze and prioritize the feedback for implementation
    - _Gather feedback from both unit users and researchers_
    - _Prioritize feedback to add new task to the backlog according to their importance_

## Consequences

- The GUI prototype should not be prioritized over the other two - this is why it's listed as objective #3.
  - If, during the key results and initiatives within objective #3 (GUI), the team finds that this is not an appropriate objective, or that there's a new, better, objective, the team can switch direction and work on the new one. In this case, the team must inform the users of the new plan.
  - For more consequences regarding the GUI, see the **Context** section above.
- The task examples listed under some of the initiatives are just that; _examples_. The team will decide on the appropriate tasks during the sprints, depending on which objective and key result they will be working on.
- The key results and initiatives _may change_ as time passes since, for example, they may depend on another initiative or information that has been gathered previous to starting the initiative.

## Footnotes

[^fn1]: https://www.whatmatters.com/faqs/okr-meaning-definition-example
