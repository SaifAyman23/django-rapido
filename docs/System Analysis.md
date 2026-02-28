## PROJECT CONFIG

```
Project Name:      Careerly
Project ID Prefix: CAREERLY
Tech Stack:
  Backend:                           Django
  Frontend:                          React
  Mobile:                            Flutter
  AI/ML:                             custom model
  Database:                          PostgreSQL
  Notifications:                     Django tasks
User Roles:                          Job Seeker, Admin
API Base URL:                        /api/v1
Flow Counter:                        Start at 001, increment per flow
Supported Platforms (scrapable)      indeed, linkedin, glassdoor, naukri
```

- the platform currently supports scraping indeed, linkedin, glassdoor, naukri
- not all data are retreived by scraping, like not all these platforms provide the description or skills

## Flows

### Auth

- Route 1 - Register:
  1. user provides (email, password, confirm password)
  2. a 6-digit OTP is sent
  3. redirected to the page with the otp input
  4. redirected to a page to choose their preferences and upload their resume (**required**)
  5. then redirected to home page successfully

- Route 2 - Login:
  1. user provides (email, password)
  2. redirected to home page

- Route 3 - Password Reset:
  1. user verfies their email by providing it then receiving an OTP
  2. the resend button is disabled for a minute
  3. on success, redirect to a page with 2 inputs (new password, confirm password)
  4. then redirect to profile


### Home page 

1. Jobs are collected and added using a scraper that runs every 15 minutes periodically (celery might be the right choice for this job)
2. the user resume is used to recommend jobs for the user in the home page
3. there is the recommended jobs section then the job listing section (jobs can be tagged as "viewed" if the user already viewed this job or "new" if new obviously (during the last 2 hours))

### Jobs

- user can view a job's details by clicking on it
- in details page the user can view the data that was scraped and organized for them
- user can save the job from the details page
- user can click on the "Apply Now" button to reach the page of the job to apply there (like linkdein job post or indeed or whatever)
- user can also click on the "AI Match" button that requests the AI to check suitability of the resume for this role
- user can save this job for applying later

from here we have 2 routes.

- Route 1 - Apply Now:
  1. User clicks on the button and is routed to the job page

### Route 2 - AI Match:
  1. AI analysis is requested for the resume to be matched against the job
  2. The AI model starts analyzing the resume to give it a suitability score
  3. and recommends the most suitable 3 jobs for the user
  4. the session is saved with the resume's title, company name and the role, the suitability score and a note for the score (NAHHHHH), and the timestamp.

### Check Your Resume

1. like the AI Match feature but a general ATS score analysis instead of tailoring to a specific job
2. the session is saved with the resume's title, file name, the ATS score and a note for the score (NAHHHHH), and the timestamp.

> the two AI features are analysis sessions, and when the AI finishes the response the user can upload another resume to match (in the AI Match, the uploaded 2nd resume will also be matched against the same role as the first resume)
> These should support markdown to enable the AI to structure properly, meaning, the AI itself should send markdown, and the frontend must support correct rendering

### Notifications
- there are system notifications and notifications sent on receiving new jobs

### Profile
- the user adds their info in edit profile page:
  1. image
  2. fullname
  3. email
  4. phone number
  5. position
  6. country
  7. biography
  8. resume (multiple files allowed)
- the profile itself show:
  1. image
  2. fullname
  3. position
  4. avg ATS score throughout the AI analysis
  5. total jobs viewed
  6. biography (must support markdown)
  7. files uploaded
  8. list of jobs viewed

### Subscription
- The user subscribes to a plan with specific features that we will plan, features govern the limitations and available merits


### Roles

- There are only 2 roles in the system:
  - job seeker that creates their profile and adds their info and views jobs
  - admin that sees the admin dashboard and is responsible for everything in the platform


### Monitoring
- Django's admin dashboard allows for what it allows for
- We want to add a way to show area charts and stuff to ensure monitoring with color codes and all

**Prompt:**
now we're going to design the "Careerly" system together OK? I will give you the flows and you will generate the descriptions for it, bullet points, necessary validations, user roles responsible for the actions in the flow, a colored mermaid sequence diagram for the flow with all the details and alternate cases.

Each flow I give you must be complete and sufficient so devs can work immediately.

First, before I give any flow, I want you to analyze the instructions I just gave you and create a mindmap so every time we work on a flow we use that mindmap







This is what we reached.



I want you to make sure each flow has 2 parts, the first part is the analysis and all the systematic stuff, and the second part is the technical part (but do not include any code).



The first part is generally covered in this guide, but the second part is recommended to have the follow:





the sequence diagrams mentioned and any kind of necessary diagrams that can improve understanding (always add sequence diagrams) and make sure all the diagrams are colored always



tables that are needed to build the models with their types (from django) and required or not and a note about each field



clear explanations on how tables work together and validations and every thing technical



notes for AI engineer, frontend engineer (react), mobile dev (flutter), backend dev(django) so each can work closely



and always add a section at the end of each flow so I can add general notes



and this is the second part, reform the guide so the two parts are clear so we can build the ultimate system designs

