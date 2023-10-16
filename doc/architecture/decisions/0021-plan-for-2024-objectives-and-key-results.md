# 21. Plan for 2024: Objectives and Key Results

Date: 2023-10-16

## Status

Accepted

## Context

The Product Owner (PO) / Project Leader (PL) of Team Hermes - responsible for the development and maintenance of the Data Delivery System (DDS) - is going on parental leave from November 17th 2023. Due do this, and that the substitute(s) / replacement(s) has not had enough time to learn the system in order to fully take over the PO / PL responsibilities, there needs to be a plan for what the team should work on during the coming year. Starting a more formal plans for the coming year (now and in the future) is also a general improvement to the team and stakeholders, since it will allow for more tranparancy outward and help guide the team's focus.

In order to plan for the coming year (2024, and December 2023), the team is using the tool _OKRs: Objects and Key Results_.

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

The issue motivating this decision, and any context that influences or constrains the decision.

### Discussions regarding possible objectives

#### "Improve user experience via UI"

##### Alternative 1: Implement the `dds-cli` functionality in the web interface.

- The web interface will not be a good way for uploads and downloads of huge amounts of data. The units are also saying this.
- Implementing the functionality in the web interface would require us to have a front-end developer that also has experience in cryptography. We (the PO mainly) have been asking- and waiting for this person for years, so we cannot expect that that's going to happen any time soon. The last time it was mentioned was both before and after summer 2023; since then we haven't heard or said anything regarding this. Therefore, creating the web interface that is envisioned - a complete reset of the web using some JS framework - is not possible.
  - Even if a front-end developer was to get hired at some point during 2024, doing a complete reset of the frontend (which houses functionality required to register, reset password, setup 2FA, etc) and building the web from scratch, while the person who has been involved in developing the majority of the code, is away, is **not** a good idea.
- If we were to work on implementing the functionality into the web interface as it is now, without having a front-end developer, we would have to continue using pure flask in the web, and that would mean that we would need to make a duplicate of practically all of the API code that exists, because:
  - Calling the API endpoints from the Flask routes does not work since those endpoints require authentication tokens - the ones that the CLI uses.
  - Moving the API code, creating helper functions, and changing everything in order to use the new helper functions in both the API and web should not be done when the PO is away; It's too much work and it risks the functionality in the web. We should be adding functionality to the system during 2024, **not** refactoring and risking working functionality to break.
- Duplicating the code for listing projects, users, files, adding users to projects (etc, etc) in the web means that we later on will have to redo it all and the team will have spent time on something that will not be used anyway since the upload and download by pure flask and html is not a good idea. Also, upload and download of potentially huge amounts of data via browser is as mentioned above not a good solution.

**Because of these things, implementing the functionality in the web interface is not an option; we won't plan for working on the web interface during the coming year.**

##### Alternative 2: Creating a Graphical User Interface (GUI)

- The unit's _end-users_ (the users downloading the data) would benefit from this.
- The NGI units that do not need the download functionality for their end users in the GUI also do not need it in the web, they just have bioinformaticians that help the users and the bioinformaticians are familiar with terminal tools
- Other smaller units have less experienced end users and are more likely to want to download locally and to want to click buttons instead of using the terminal
- This GUI would be very simple to begin with, it could (for example) be created by `tkinter` or another simple package (google "simple GUI python" or similar, there are several). The main thing here is that we should not need to write new code for the actual DDS functionality; The idea is that the GUI would run the CLI commands when buttons are clicked etc. Buttons would run the commands, and the same things that are displayed in the CLI would be displayed in the GUI.
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

> **Objective X: [short goal] -- [long goal]**
>
> - **Key Result 1 [COMMITTED / ASPIRATIONAL / LEARNING]:** [Description / goal]
> - **Key Result 2 [COMMITTED / ASPIRATIONAL / LEARNING]:** [Description / goal]
> - **Key Result X [COMMITTED / ASPIRATIONAL / LEARNING]:** [Description / goal]

### Objective 1: GUI -- "Improve user experience via UI"

- **Reduced learning curve:** Users can perform common tasks in the new GUI in less time and effort compared to the CLI (ASPIRATIONAL/LEARNING)
- **Feature adoption:** Increase the adoption rate of the GUI features by XX % within xx months of launch, by measuring the number of asset downloads (ASPIRATIONAL/LEARNING)
- **Cross-Platform Consistency:** Ensure the GUI functions consistency and seamlessly on the OSs macOS, Linux and Windows (different distributions. (ASPIRATIONAL/LEARNING)

### Objective 2: Support -- "Optimize support"

- **Workshop for users:** Plan for a workshop for DDS users; The workshop should be run at least once a year. (COMMITTED)
- **Support documentation:** Create or update support documentation for the top 5 most common support inquiries to facilitate self-service (COMMITTED)
- **Ticket Volume:** Reduce the number of "irrelevant" support tickets submitted by 50% percent within the next 6 months months, by implementing a chatbot in the web interface. "Irrelevant": questions that should go to units or that units should already know. (ASPIRATIONAL)
  Initiatives: Create chatbot, provide answers for x, ask "was this helpful" and measure

### Objective 3: Quality -- "Improve software quality"

- **Resolve security alerts:** Resolve all solvable (with known fixes) critical security alerts within 7 days, high-severity alerts within 14 days and medium-severity alerts within a month. (ASPIRATIONAL)
- **Test coverage:** Increase test coverage for dds_web to 100% and dds_cli to 70% (ASPIRATIONAL)
- **API documentation:** Create / Generate documentation for the dds_web/api, which covers all endpoints. (COMMITTED)

## Consequences

What becomes easier or more difficult to do and any risks introduced by the change that will need to be mitigated.

## Footnotes

[^fn1]: https://www.whatmatters.com/faqs/okr-meaning-definition-example
