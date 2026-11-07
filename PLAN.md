# Build Plan: Agentic Build Workflow

Talk to a Grok Bot about an idea. A team of AI agents on the Swarms API plans it, Cursor writes the code, Grok Bot tests it like a real user, and nothing ships until you approve it.

- **Hackathon:** 48 hours, solo
- **Targets:** Best Use of Swarms API, and the SpaceXSI raffle (Cursor + Grok Bot)
- **Language:** Python
- **Diagrams:** [FigJam board](https://www.figma.com/board/dJnSw0KY8UYIcxjXPz5bcq) has the system map, the feature sequence, first-time setup, new idea to new repo, and the credentials map.

---

## Contents

1. [How it works in one minute](#1-how-it-works-in-one-minute)
2. [Components and who runs what](#2-components-and-who-runs-what)
3. [Repositories](#3-repositories)
4. [Grok Bot: the three bots](#4-grok-bot-the-three-bots)
5. [First-time setup (what Project Lead tells a new user)](#5-first-time-setup-what-project-lead-tells-a-new-user)
6. [Swarms: agents and phases](#6-swarms-agents-and-phases)
7. [The orchestrator](#7-the-orchestrator)
8. [Commands and state](#8-commands-and-state)
9. [Flows end to end](#9-flows-end-to-end)
10. [How Cursor builds the code](#10-how-cursor-builds-the-code)
11. [Credentials](#11-credentials)
12. [Setup tests (do these first)](#12-setup-tests-do-these-first)
13. [Build timeline](#13-build-timeline)
14. [Scope: must, should, could](#14-scope-must-should-could)
15. [Risks and fallbacks](#15-risks-and-fallbacks)
16. [Demo script (3 minutes)](#16-demo-script-3-minutes)
17. [Submission checklist](#17-submission-checklist)
18. [Using this plan in Cursor](#18-using-this-plan-in-cursor)
19. [Not verified yet](#19-not-verified-yet)

---

## 1. How it works in one minute

```
You (Grok Bot app) ──► Project Lead bot ──► posts a command on a GitHub issue
                                                   │
                                     GitHub Actions starts orchestrator.py
                                                   │
                                 Swarms API runs the right team of agents
                                                   │
                     results saved in the repo + summary comment on the issue
                                                   │
                     webhook ──► Project Lead asks you: "Approve?" ──► you: "Go"
                                                   │
                 Project Lead launches Cursor Cloud Agents ──► PRs with real code
                                                   │
       Swarms reviews the PR ─► Vercel preview ─► QA Tester tests it ─► Release Vote
                                                   │
                         you say "Go" ──► merged and deployed ──► screenshots to you
```

**The split between the three tools:**

| Tool | Role | Why |
|---|---|---|
| **Swarms API** | The brain: every agent that thinks, writes plans, reviews or votes | Agents return text and decisions. They can't edit files or run code. |
| **Cursor Cloud Agents** | The hands: write the code, run it, fix it, open PRs | They have their own machine, so they can run code, see errors and fix them. |
| **Grok Bot** | The voice and the eyes: talks to you, asks for approvals, clicks through apps, tests the live app, sends screenshots | It works on its own cloud computer like a person does. |

**Rule:** agents decide, code acts. A Swarms agent can say "merge PR #3 with squash", but `orchestrator.py` is what calls the GitHub API to do it, and only after your approval.

---

## 2. Components and who runs what

You don't run any server. Everything runs on someone else's machine.

| Component | Runs on | Cost |
|---|---|---|
| `orchestrator.py` | GitHub Actions: a temporary Linux machine per run, deleted afterwards | Free on public repos. 2,000 minutes a month free on private repos. |
| Swarms agents | Swarms API | Your Swarms credits |
| Cursor Cloud Agents | Cursor's cloud | Your Cursor plan |
| Project Lead, Progress Reporter, QA Tester | Grok Bot's cloud computer | Your Grok Bot plan |
| The product (English app) | Vercel (Hobby plan) | Free |

The orchestrator has no memory between runs. **The repo is the memory:** docs, tasks, PRs, issue comments and labels.

---

## 3. Repositories

### Home base: `sharkbyte_hackathon`

Created once per user. It holds the code and the Idea Inbox.

```
sharkbyte_hackathon/
├── PLAN.md                         ← this file
├── README.md                       ← what it is + "create your Project Lead bot" instructions
├── projects.json                   ← your projects: {"english-app": "https://github.com/<you>/english-app"}
├── orchestrator/                   ← ALL orchestrator code lives here (single source)
│   ├── main.py                     ← entry point: reads the GitHub event, routes the command
│   ├── github_io.py                ← comments, labels, files, PRs, merges, repo creation, secrets
│   ├── swarms_client.py            ← thin wrapper over the Swarms HTTP API
│   ├── notify.py                   ← calls the Grok Bot webhooks
│   ├── state.py                    ← reads/writes phase + status labels
│   ├── parsing.py                  ← pulls the JSON block out of agent output
│   ├── phases/
│   │   ├── idea_lab.py
│   │   ├── discovery.py
│   │   ├── design.py
│   │   ├── plan.py
│   │   ├── feature.py
│   │   ├── review.py
│   │   ├── vote.py
│   │   ├── release.py
│   │   ├── status.py
│   │   └── create_project.py
│   └── agents/                     ← one JSON file per swarm (agent specs + system prompts)
│       ├── idea_lab.json
│       ├── deep_dive.json
│       ├── design.json
│       ├── plan.json
│       ├── feature_story.json
│       ├── review.json
│       ├── release_vote.json
│       ├── release.json
│       └── single.json             ← Scrum Master, Formatter
├── template/                       ← copied into every new project repo
│   ├── .github/workflows/agent.yml
│   ├── .cursor/rules/project.mdc
│   ├── docs/README.md
│   ├── .gitignore
│   └── .env.example
├── .github/workflows/home.yml      ← Idea Inbox commands, /ping, create project, morning digest
├── requirements.txt                ← requests, PyGithub, python-dotenv
├── .gitignore                      ← includes .env
└── .env.example
```

### One repo per project, for example `english-app`

Created by the **create project** workflow. Everything about this project lives here: the project issue, feature issues, docs, tasks and PRs.

```
english-app/
├── .github/workflows/agent.yml   ← thin trigger; checks out home base to get orchestrator/
├── .cursor/rules/project.mdc     ← stack + conventions, written by the Cursor Prompt Writer
├── docs/
│   ├── IDEA.md                   ← idea + Idea Lab score card
│   ├── PRD.md                    ← Deep Dive output
│   ├── DESIGN.md                 ← architecture, UX, final scope
│   └── ACCEPTANCE.md             ← acceptance criteria QA Tester checks
├── tasks/
│   ├── 001-<name>.md             ← one task per Cursor Cloud Agent
│   └── ...
├── CHANGELOG.md                  ← written by the Docs & Pitch Writer on each release
└── (app code written by Cursor)
```

**Why the orchestrator code stays in home base:** each project's workflow checks out home base at run time, so a fix in the orchestrator applies to every project at once. Each project only gets a thin trigger workflow and its own secrets.

**The rule for ideas:**
- A new idea that isn't related to an existing project goes to the **Idea Inbox** (an issue in home base), with no repo yet.
- It only gets its own repo when you say "build it" **and** approve the repo name and visibility.
- An idea for an existing project becomes a **feature issue in that project's repo**.

---

## 4. Grok Bot: the three bots

All three live in the **Grok Bot app**. You only talk to **Project Lead**. The other two report to you.

### Project Lead: your only conversation partner

**Does:**
- runs first-time setup
- captures ideas and decides between the Idea Inbox and an existing project
- asks you the open questions the agents generate
- presents results and collects approvals
- posts commands on GitHub
- launches Cursor Cloud Agents
- connects new repos to Vercel

**Instructions to paste when creating the bot** (draft):

```
You are Project Lead. You help me turn ideas into working software using my agentic
build system (home base repo: <home base URL>). I only talk to you.

How you work:
- If you have no note saying "Setup complete", run the Setup routine first.
- When I share an idea, read projects.json in home base. If the idea belongs to an
  existing project, create a feature issue in that repo and comment "/run feature".
  Otherwise create an issue in home base with the label "idea" and comment "/score".
- When a webhook arrives, read the linked issue or PR, summarize it in 3-5 short lines,
  and ask me exactly the question in the payload. Post my answer as a command:
  "Go"/"yes" -> "/approve", feedback -> /revise "<my words>".
- Never create a repo, merge, or release without my explicit yes in this chat.
- Never paste secrets, tokens or keys in chat or on GitHub.
- Commands you may post: /score, /build, /run, /approve, /revise, /vote, /release, /status, /ping.
- Keep messages short. Always include the link to the issue or PR.
```

**Routines:**

| Routine | Trigger | What it does |
|---|---|---|
| Setup | First chat, or "help me set up" | Walks you through [section 5](#5-first-time-setup-what-project-lead-tells-a-new-user), step by step, then posts `/ping` |
| New idea | You share an idea | Decides between Inbox and existing project, creates the issue, posts the command |
| Message me | **Webhook** from the orchestrator | Reads the payload, summarizes, asks you, posts your answer as a command |
| Build task | Webhook "tasks ready" | Launches one Cursor Cloud Agent per task, in order (see [section 10](#10-how-cursor-builds-the-code)) |
| Fix request | Webhook "changes requested" | Sends the review comments to the same Cursor agent as a follow-up |
| Connect Vercel | Webhook "repo created" | Imports the new repo in the Vercel dashboard |
| Morning digest | Webhook from the scheduled home base run | Sends you the top 3 ideas from the Inbox |

### Progress Reporter: what happened, with screenshots

**Does:** sends you the GitHub feed (PRs opened, reviews, merges, deploys) and screenshots of the live app and the PR pages.

**Instructions to paste when creating the bot** (draft):

```
You are Progress Reporter. When a webhook arrives, open the links in it (PR page,
preview URL, production URL), take screenshots, and send me one short update:
what happened, the status, and the screenshots. If I ask "show me the app", open the
latest preview or production URL from the most recent update and send screenshots.
Never change anything on GitHub. You only read and report.
```

**Routines:**

| Routine | Trigger | What it does |
|---|---|---|
| Event update | **Webhook** (PR opened, review posted, preview ready, merged, live) | Screenshots + 2–3 line summary |
| Digest | Schedule, every 2 hours (fallback if webhooks fail) | Checks the repos and summarizes what changed |
| Show me | You ask | Opens the app, sends screenshots |

### QA Tester: tests every preview like a real user

**Does:** opens the Vercel preview, walks through each acceptance criterion, takes screenshots, reports pass or fail on the PR, and files bugs.

**Instructions to paste when creating the bot** (draft):

```
You are QA Tester. When a webhook gives you a preview URL and a PR link, open
docs/ACCEPTANCE.md (or the acceptance criteria in the linked issue) and test each
criterion on the preview like a real user. Take a screenshot for each one.
Post ONE comment on the PR in this exact format:

QA RESULT: PASS 3/4
- [x] criterion 1
- [ ] criterion 2 - what went wrong, steps to reproduce
(screenshots)

Then post a separate comment with only: /vote
For each failed criterion, also open a bug issue in the same repo with the label "bug".
```

**Routines:**

| Routine | Trigger | What it does |
|---|---|---|
| Test preview | **Webhook** "preview ready" | Tests acceptance criteria, posts the QA RESULT comment, then `/vote` |
| Smoke test production | Webhook "live" | Quick check that the main page and the new feature work |

> Grok Bot uses **your** GitHub login. Its comments appear as you, so they pass the "only the owner can run commands" check.

---

## 5. First-time setup (what Project Lead tells a new user)

This is the **Setup routine**. It's the first thing Project Lead does with a new user, whether a hacker or a non-technical founder. It explains each step in plain words, waits for "done", checks when it can, and moves on. The diagram is on the FigJam board ("First-Time Setup").

**Step 0, done by the user before talking to the bot:** create the Project Lead bot in the Grok Bot app with the instructions from the home base README.

| # | Step | What Project Lead says / checks |
|---|---|---|
| 1 | **Accounts** | You need: a GitHub account; a Swarms account with an API key and credits; Cursor Pro or SuperGrok (for Grok Bot); a Vercel Hobby account. |
| 2 | **Home base repo** | Open the home base template on GitHub → **Use this template** → name it → create. Send me the link. *(Check: it opens the repo.)* |
| 3 | **The other two bots** | Create Progress Reporter and QA Tester with the instructions I'll paste. In each bot's routines, copy the **webhook URL**. Also copy mine. *(3 URLs.)* |
| 4 | **GitHub token** | GitHub → Settings → Developer settings → **Fine-grained tokens** → Generate. Access: **All repositories**. Permissions: **Administration, Contents, Pull requests, Issues, Secrets**: read and write; **Actions**: read. Copy it. Don't paste it here. |
| 5 | **Secrets** | Home base → Settings → **Secrets and variables → Actions** → New repository secret. Add: `SWARMS_API_KEY`, `GH_TOKEN`, `PROJECT_LEAD_WEBHOOK`, `PROGRESS_REPORTER_WEBHOOK`, `QA_TESTER_WEBHOOK`. *(Check: Settings shows 5 secret names.)* |
| 6 | **Cursor** | Cursor dashboard → connect **GitHub**. On the **Grok Bot** page, make sure **Cloud Agents** is on. If you use Legacy Privacy Mode, switch to a supported data setting. |
| 7 | **Vercel** | Sign in to Vercel with GitHub so it can see your repos. |
| 8 | **Health check** | I'll post `/ping` in your home base. If everything works, the orchestrator replies and calls all three bots' webhooks. You'll get "Setup complete ✅". |

**`/ping` checks:**
- the workflow runs
- the Swarms key works (tiny 1-agent call)
- the GitHub token can read repos and write issues
- each of the three webhooks answers

It reports each check as ✅ or ❌, with the step number to fix.

**Stretch:** Project Lead does the clicks for steps 2, 5 and 7 itself in its browser, and the user only approves. Keep the token step manual, so the user always creates and holds their own key.

---

## 6. Swarms: agents and phases

### Phases

Each phase uses the swarm type that fits the job. This is the core of the "Best Use of Swarms API" story.

| Phase | Agents | Swarm type | Why this type | Output (file) | Gate |
|---|---|---|---|---|---|
| **Idea Lab** | Idea Scout, Market Researcher, Feasibility Analyst, MVP Cutter | `ConcurrentWorkflow` | Independent views, run in parallel | Score card + open questions (`docs/IDEA.md` when a project is created) | — |
| **Deep Dive** | Product Owner (leads), Product Manager, UX Researcher | `HierarchicalSwarm` | The PO owns the backlog and directs the others | `docs/PRD.md`, `docs/ACCEPTANCE.md` | ✅ Approve PRD |
| **Design** | Architect, UX/UI Designer, Security Reviewer, MVP Cutter | `GroupChat` | Trade-offs need debate | `docs/DESIGN.md` (stack, data model, pages, scope in/out) | ✅ Approve scope |
| **Plan** | Tech Lead → Cursor Prompt Writer | `SequentialWorkflow` | Each step refines the last | `tasks/*.md`, `.cursor/rules/project.mdc` | — |
| **Feature story** (fast path) | Product Owner → MVP Cutter | `SequentialWorkflow` | Story first, then trim | Story + acceptance criteria in the feature issue | ✅ Approve story |
| **Code Review** | Code Reviewer, Security Reviewer | `ConcurrentWorkflow` | Independent checks on the same diff | PR review comment | — |
| **Release Vote** | QA Analyst, Code Reviewer, Security Reviewer, Product Owner | `MajorityVoting` | A real vote: each gives Go or No-Go with a reason | Vote table on the PR | ✅ Your final Go |
| **Release** | PR & Merge Manager → DevOps/Release → Docs & Pitch Writer | `SequentialWorkflow` | Merge plan, then deploy check, then notes | Merge decision (JSON), `CHANGELOG.md`, README update | — |
| **Status** | Scrum Master | single agent | Summarize the issue timeline | `/status` reply | — |
| **Bug triage** *(stretch)* | Bug Triage Router → specialist | `MultiAgentRouter` | Each bug goes to the right specialist | Labels + fix task | — |

### Agent roster

| Agent | Responsibility | Used in |
|---|---|---|
| Idea Scout | Restates the idea: user, problem, value. Lists open questions. | Idea Lab |
| Market Researcher | Similar products, what's different, who would pay | Idea Lab |
| Feasibility Analyst | Can an MVP be built fast? Technical risks. | Idea Lab |
| MVP Cutter | The smallest version that still shows the value. Cuts everything else. | Idea Lab, Design, Feature story |
| Product Owner | Owns the backlog. Writes user stories and acceptance criteria. Final say on scope. | Deep Dive, Feature story, Release Vote |
| Product Manager | Discovery: goals, personas, success metrics | Deep Dive |
| UX Researcher | User journeys, main pain points | Deep Dive |
| Architect | Stack, data model, APIs, deployment. Default: Next.js + Supabase on Vercel. | Design |
| UX/UI Designer | Pages, components, layout, copy, accessibility basics | Design |
| Security Reviewer | Auth, secrets, input validation, data exposure | Design, Code Review, Release Vote |
| Tech Lead | Breaks the design into 3–6 small tasks with dependencies | Plan |
| Cursor Prompt Writer | Turns each task into a Cursor-ready `tasks/NNN-*.md` and writes `.cursor/rules` | Plan |
| Code Reviewer | Reviews the PR diff: bugs, readability, matches the task | Code Review, Release Vote |
| QA Analyst | Reads the QA Tester's report and judges release readiness | Release Vote |
| PR & Merge Manager | Merge or not, merge method, conflicts, branch cleanup | Release |
| DevOps/Release | Deploy checklist, env vars needed, rollback note | Release |
| Docs & Pitch Writer | CHANGELOG, README section, Devpost-style summary | Release |
| Scrum Master | Progress summary: done, in progress, blocked, next | Status |
| Formatter | Converts any free-text output into the required JSON | Any phase, as a fallback |

### Agent spec format (`orchestrator/agents/*.json`)

Field names are confirmed by S1 (`tests/s1_request.json` has the exact body that worked). The request body also needs a top-level `task` string. S1 showed it is required.

```json
{
  "name": "deep-dive",
  "description": "Turn an idea into a PRD with user stories and acceptance criteria",
  "swarm_type": "HierarchicalSwarm",
  "max_loops": 1,
  "agents": [
    {
      "agent_name": "Product Owner",
      "description": "Owns the backlog and acceptance criteria; directs the team",
      "system_prompt": "You are the Product Owner... End your answer with a ```json block matching the schema in the task.",
      "model_name": "openrouter/x-ai/grok-4.3",
      "role": "director",
      "max_loops": 1
    }
  ]
}
```

### Output contract

Every phase asks for a final ` ```json ` block with a fixed schema. `parsing.py` takes the **last** JSON block in the output. If parsing fails, the orchestrator calls the **Formatter** agent once with the raw text and the schema. Every raw response is also saved as a GitHub Actions artifact for debugging.

**Example: Release Vote schema**

```json
{
  "votes": [
    {"agent": "QA Analyst", "vote": "GO", "reason": "4/4 criteria passed"},
    {"agent": "Security Reviewer", "vote": "NO_GO", "reason": "API key in client bundle"}
  ],
  "result": "HOLD",
  "blocking_issues": ["Move API key to server route"]
}
```

### Models

Confirmed in S1:
- `grok-4` returns 404. Use `openrouter/x-ai/grok-4.3`, which works. The list of valid names is at `GET /v1/models/available`.
- Use the Grok model for some agents, to tie both sponsors together.
- Use your strongest available model for the Product Owner, the Architect and the Code Reviewer.
- Keep the model name in one config value so it's easy to switch.

---

## 7. The orchestrator

### What one run does

1. GitHub event arrives: a comment, a PR, a deployment status, a schedule, or a manual run.
2. `main.py` checks:
   - the comment author is the repo owner
   - the comment starts with `/`
   - the command is valid for the current phase label
3. It reads the context: issue body and comments, `docs/*.md`, the PR diff for reviews.
4. It runs the phase's swarm through `swarms_client.py`.
5. It parses the JSON, writes files (commits docs to `main`), posts a summary comment, and updates labels.
6. It calls the right Grok Bot webhook (`notify.py`).
7. It exits.

### Workflow triggers

**Home base (`home.yml`):**
- `issue_comment`: `/score`, `/build`, `/ping`, `/status`
- `schedule`: the morning digest (Idea Lab ranking of open `idea` issues)
- `workflow_dispatch`: manual testing

**Project template (`agent.yml`):**
- `issue_comment`: `/run`, `/approve`, `/revise`, `/vote`, `/release`, `/status`
- `pull_request` (`opened`, `synchronize`): Code Review
- `deployment_status` (state `success`): "preview ready" or "live", depending on the environment. Sends the URL to QA Tester and Progress Reporter.
- `workflow_dispatch`

### `agent.yml` sketch (project repo)

```yaml
name: agent
on:
  issue_comment: { types: [created] }
  pull_request: { types: [opened, synchronize] }
  deployment_status:
  workflow_dispatch:

concurrency:
  group: agent-${{ github.event.issue.number || github.event.pull_request.number || github.run_id }}
  cancel-in-progress: false

permissions:
  contents: write
  issues: write
  pull-requests: write

jobs:
  run:
    if: >
      github.event_name != 'issue_comment' ||
      (github.event.comment.user.login == github.repository_owner &&
       startsWith(github.event.comment.body, '/'))
    runs-on: ubuntu-latest
    timeout-minutes: 30
    steps:
      - uses: actions/checkout@v4                      # this project repo
      - uses: actions/checkout@v4                      # home base, for orchestrator/
        with:
          repository: ${{ github.repository_owner }}/sharkbyte_hackathon
          path: home
          token: ${{ secrets.GH_TOKEN }}
      - uses: actions/setup-python@v5
        with: { python-version: '3.12' }
      - run: pip install -r home/requirements.txt
      - run: python home/orchestrator/main.py
        env:
          SWARMS_API_KEY: ${{ secrets.SWARMS_API_KEY }}
          GH_TOKEN: ${{ secrets.GH_TOKEN }}
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
          PROJECT_LEAD_WEBHOOK: ${{ secrets.PROJECT_LEAD_WEBHOOK }}
          PROGRESS_REPORTER_WEBHOOK: ${{ secrets.PROGRESS_REPORTER_WEBHOOK }}
          QA_TESTER_WEBHOOK: ${{ secrets.QA_TESTER_WEBHOOK }}
          EVENT_NAME: ${{ github.event_name }}
          EVENT_PATH: ${{ github.event_path }}
```

### Rules for the orchestrator code

- **Pass user text through `env:` or the event file**, never `${{ }}` inside `run:`. That blocks command injection.
- **Use `GITHUB_TOKEN` for comments and labels** in the current repo. Events it creates don't trigger new workflow runs, so the orchestrator can't loop on itself.
- **Use `GH_TOKEN` (your fine-grained token) only for:**
  - creating repos
  - copying secrets
  - merging
  - reading home base
- **The orchestrator's own comments never start with `/`.**
- **`concurrency` per issue or PR**, so two runs never work on the same thing at once.
- **Swarms calls:** timeout of about 10 minutes, 2 retries on network errors, and the raw response saved as an artifact.
- **Use raw `requests` in `swarms_client.py`** (about 40 lines) instead of the SDK. Search results show SDK method names changing between versions.
- **Never put secrets in prompts.** Prompts only contain docs, issue text and diffs.

### Webhook payload to Grok Bot (our own format)

```json
{
  "event": "approval_needed",
  "repo": "https://github.com/<you>/english-app",
  "link": "https://github.com/<you>/english-app/issues/1",
  "summary": "PRD ready: 5 user stories, 12 acceptance criteria.",
  "question": "Approve the PRD? Reply Go, or tell me what to change.",
  "preview_url": null
}
```

Event types:
- `approval_needed`, `tasks_ready`, `changes_requested`
- `pr_opened`, `review_posted`, `preview_ready`
- `vote_result`, `merged`, `live`
- `repo_created`, `digest`, `ping`

---

## 8. Commands and state

### Commands

**Home base (Idea Inbox issue):**

| Command | Who posts it | What runs |
|---|---|---|
| `/score` | Project Lead (after creating the idea issue) | Idea Lab → score card + open questions |
| `/build <repo-name> public\|private` | Project Lead, **after you approve the name** | Create project workflow |
| `/ping` | Project Lead (setup) or you | Health check |
| `/status` | Anyone (owner) | Scrum Master summary of open ideas and projects |

**Project repo:**

| Command | Where | What runs |
|---|---|---|
| `/run discovery` | Project issue (posted automatically after create project) | Deep Dive → PRD |
| `/run feature` | Feature issue | Feature story |
| `/approve` | Issue | Next phase for the current label |
| `/revise "<feedback>"` | Issue | Same phase again, with your feedback added |
| `/vote` | PR (QA Tester posts it after testing) | Release Vote |
| `/release` | PR, **after your Go** | Release swarm → merge → deploy |
| `/status` | Any issue | Scrum Master summary |

### State, stored as labels

The orchestrator only accepts a command that makes sense for the current label.

- **Phase labels:**
  - project issue: `phase:discovery` → `phase:design` → `phase:plan` → `phase:build` → `phase:done`
  - feature issue: `phase:story` → `phase:plan` → `phase:build` → `phase:done`
- **Status labels:** `status:running`, `status:waiting-approval`, `status:waiting-go`, `status:blocked`
- **PR labels:** `task:NNN`, `review:pass` or `review:changes`, `qa:pass` or `qa:fail`, `vote:go` or `vote:hold`

---

## 9. Flows end to end

### A. New idea → new project

1. You tell Project Lead an idea. It checks `projects.json`, finds it's new, and creates an Idea Inbox issue + `/score`.
2. Idea Lab scores it. Project Lead sends you the score and the open questions, and you answer them in chat. Project Lead adds your answers to the issue.
3. You say "build it". Project Lead asks for the repo name and public or private. You approve, and it posts `/build english-app public`.
4. The create project workflow:
   - creates the repo
   - copies `template/` into it
   - copies the 5 secrets (PyGithub `create_secret` handles the encryption)
   - opens the project issue with the idea, the score and your answers
   - adds the repo to `projects.json`
   - posts `/run discovery` using `GH_TOKEN`, so the new repo's workflow starts
   - sends the `repo_created` webhook
5. Project Lead imports the repo in Vercel.
6. Deep Dive → PRD → ✅ → Design → ✅ → Plan → `tasks_ready` → flow C.

### B. New feature for an existing project (the live demo)

1. You: "Add a daily vocab quiz to the English app". Project Lead finds `english-app` in `projects.json`, creates a feature issue, and posts `/run feature`.
2. Feature story (PO → MVP Cutter) → story + acceptance criteria → ✅ your approval.
3. Plan → `tasks/*.md` → `tasks_ready` → flow C.

### C. Build, review, test, release (shared by A and B)

1. Project Lead launches a Cursor Cloud Agent for `tasks/001-*.md`, then waits for the PR.
2. PR opened → Code Review swarm → review comment. If it asks for changes, the `changes_requested` webhook goes to Project Lead, which sends a follow-up to the same Cursor agent. **Maximum 2 rounds**, then ask you.
3. Vercel preview ready (`deployment_status`) → QA Tester tests → `QA RESULT` comment → `/vote`.
4. Release Vote (`MajorityVoting`) → vote table on the PR → `vote_result` to Project Lead → "4/4 Go. Launch?"
5. You say "Go" → Project Lead posts `/release`.
6. The Release swarm decides the merge method and writes the CHANGELOG. The orchestrator merges with `GH_TOKEN`, and Vercel deploys production.
7. Production `deployment_status` → Progress Reporter sends screenshots of the live app, and QA Tester runs a smoke test.
8. Next task, or `phase:done`.

---

## 10. How Cursor builds the code

**Main path: Grok Bot launches Cursor Cloud Agents.**
- This integration exists: in the Cursor dashboard, the Grok Bot page has a team-wide **Cloud Agents** setting, on by default.
- A Cloud Agent clones the repo in its own VM, writes and runs the code, pushes a branch and opens a PR.

**What Project Lead sends Cursor for each task:**

```
Repository: https://github.com/<you>/english-app
Read .cursor/rules/project.mdc and tasks/003-vocab-quiz.md.
Implement only that task. Run the app and the tests before you finish.
Open a PR titled "[task-003] Vocab quiz" whose description says "Part of #<issue number>".
```

**The PR title format `[task-NNN]` is how the orchestrator links** a PR → its task file → its issue.

**Task rules (enforced by the Tech Lead and the Cursor Prompt Writer):**
- 3–6 tasks per project and 1–3 per feature. Each should be small enough for one PR.
- Tasks run **one at a time** in dependency order, to avoid merge conflicts.
- Every task file has these sections:
  - Goal
  - Files to touch
  - Steps
  - Acceptance criteria
  - "Done when"
  - Out of scope

**Plan B: the orchestrator launches the agents.** If Grok Bot's launch is flaky, the orchestrator calls the Cursor Cloud Agents API on `tasks_ready` (needs a `CURSOR_API_KEY` secret). Community docs describe `POST /v0/agents` with a prompt and a source repo. Check Cursor's official API reference before using it.

**You also use Cursor yourself:** you build `orchestrator/` in Cursor's editor in Agent mode. Keep screenshots of those chats for the submission. That's the "Cursor as core AI coding agent" requirement.

---

## 11. Credentials

The diagram is on the FigJam board ("Credentials Map").

| Credential | Where it lives | Used by |
|---|---|---|
| `SWARMS_API_KEY` | Home base Actions secret, copied to each project | orchestrator |
| `GH_TOKEN` (fine-grained) | Home base Actions secret, copied to each project | orchestrator: create repo, copy secrets, merge, read home base |
| `PROJECT_LEAD_WEBHOOK`, `PROGRESS_REPORTER_WEBHOOK`, `QA_TESTER_WEBHOOK` | Actions secrets. They are secrets: anyone with the URL can trigger your bot. | orchestrator → Grok Bot |
| `CURSOR_API_KEY` *(plan B only)* | Actions secret | orchestrator → Cursor |
| Your GitHub login (for the bots) | Grok Bot secure secrets handoff, never in chat | Project Lead, QA Tester |
| App keys (database, AI API…) | Vercel environment variables, plus Cursor cloud agent secrets for tests | the English app |
| Local copies | `.env` on your laptop (in `.gitignore`), plus `.env.example` committed with names only | you, testing locally |

**Rules:**
- `.env` goes in `.gitignore` **before the first commit**.
- Turn on **secret scanning + push protection** (free on public repos).
- Never put secrets in Swarms prompts. Agent output gets committed to a public repo.
- **Fine-grained token permissions:**
  - only your repos, including future ones
  - **Administration**, **Contents**, **Pull requests**, **Issues**, **Secrets**: read and write
  - **Actions**: read
- **After the hackathon:** rotate every key, then make the repos private. Cursor, Vercel and the bots may then need access granted again.

---

## 12. Setup tests (do these first)

These decide the final wiring. Write down the result of each one.

| # | Test | Pass means | If it fails |
|---|---|---|---|
| S1 | **Swarms hello world:** 2 agents, `SequentialWorkflow`, `POST /v1/swarm/completions`, `x-api-key` header. Try a Grok `model_name`. Then try `HierarchicalSwarm`, `GroupChat` and `MajorityVoting` with 2 tiny agents each. | You know the exact request fields, the response shape, and the working model names | Use the swarm types that work. Fall back to `SequentialWorkflow`/`ConcurrentWorkflow` and say so honestly. |
| S2 | **Grok Bot webhook:** create a "Message me" routine, call its webhook with `curl` and a JSON body | The bot messages you with the payload content | Polling: a routine every 5 minutes checks for issues labeled `status:waiting-approval` |
| S3 | **Grok Bot → GitHub:** ask Project Lead to create an issue and post a comment in a test repo | The issue and comment appear (as you) | You type the commands yourself, so the flow still works |
| S4 | **Grok Bot → Cursor:** ask Project Lead to start a Cloud Agent on a test repo: "add a /health page" | You get a PR link back in chat | Plan B: Cursor Cloud Agents API from the orchestrator |
| S5 | **Screenshots:** ask Progress Reporter to open a URL and send a screenshot | An image arrives in the Grok Bot app | Report links + text only |
| S6 | **Vercel:** import a test repo, open a PR | A preview URL appears and a `deployment_status` event fires | QA Tester gets the URL from the PR page instead |
| S7 | **Actions round trip:** a minimal workflow that replies to `/ping` | The reply comment appears within about a minute | Check the `if:` condition and the workflow permissions |

---

**S1 result: passed.** HTTP 200 with text from both agents, using `SequentialWorkflow`. Findings:
- `grok-4` returns 404. Working model: `openrouter/x-ai/grok-4.3`.
- The body needs a top-level `task` field.
- Saved as `tests/s1_request.json` and `tests/s1_response.json`, with no key in either file.
- Still untested: `HierarchicalSwarm`, `GroupChat`, and `MajorityVoting`. Run them in a follow-up test (S1b) before Block 2.

## 13. Build timeline

The hackathon has already started. Adjust the blocks to the hours you have left. Sleep is part of the plan.

| Block | Hours | Goal | Done when |
|---|---|---|---|
| **0. Setup tests** | 3 | S1–S7 | Every test has a pass/fail note, and the wiring is decided |
| **1. Skeleton** | 3 | Repo layout, `requirements.txt`, `.gitignore`, secrets, `home.yml`, `/ping` round trip including webhooks | Project Lead says "Setup complete ✅" |
| **2. First phases** | 5 | `swarms_client.py`, `parsing.py`, `state.py`, `github_io.py`; agent JSON for Idea Lab + Deep Dive; `/score`, `/run discovery`, `/approve`, `/revise` | An idea becomes a PRD in the repo, and you approve it from the Grok Bot app |
| 😴 **Sleep** | 5–6 | | |
| **3. Design, Plan, Create project** | 5 | Design + Plan phases → `tasks/*.md` + rules; create project workflow (if behind, create `english-app` by hand) | `english-app` exists with PRD, DESIGN, tasks and rules |
| **4. Build + Review** | 5 | Project Lead "Build task" routine; `pull_request` → Code Review; fix loop | Cursor opens a PR and the review swarm comments on it |
| **5. Test + Vote + Release** | 4 | `deployment_status` → QA Tester + Progress Reporter; Release Vote; `/release` → merge | One task goes from PR to production with your "Go" |
| 😴 **Sleep** | 5 | | |
| **6. Feature fast path + dry run** | 4 | `/run feature`; full run on the English app; fix what breaks | "Add a daily vocab quiz" works end to end |
| **7. Polish + demo** | 3 | Setup routine polish, README, Docs & Pitch output, record the demo, collect screenshots | Demo video recorded |
| **8. Submit** | 2 | Submission text, raffle opt-in, buffer | Submitted |

---

## 14. Scope: must, should, could

| Priority | Items |
|---|---|
| **Must** | Project Lead in the Grok Bot app; `/ping`; Deep Dive → PRD with approval gate; Plan → tasks + Cursor rules; Cursor PR; Code Review swarm; Release Vote; `/release` merge; feature fast path |
| **Should** | Create project workflow (new repo per idea); QA Tester on previews; Progress Reporter screenshots; Idea Lab scoring; Design phase with `GroupChat` |
| **Could** | Morning digest; Bug triage (`MultiAgentRouter`); automatic Vercel import by Project Lead; the bot doing setup clicks for the user |
| **Not this weekend** | Web dashboard; Slack "team mode"; multiple users per home base |

**Cut order if you fall behind:** morning digest → bug triage → automatic Vercel import → create project workflow (create the repo by hand) → Design as its own phase (merge it into Plan).

---

## 15. Risks and fallbacks

| Risk | Fallback |
|---|---|
| Grok Bot webhooks don't work | Scheduled routines poll GitHub for `status:waiting-*` labels every 5 minutes |
| Grok Bot can't launch Cursor agents reliably | Cursor Cloud Agents API from the orchestrator (`CURSOR_API_KEY`) |
| Grok Bot is slow or flaky on GitHub clicks | You post the command yourself. The flow and the demo still work. |
| A swarm type errors or returns odd output | The swarm type is set per phase in config; switch to `SequentialWorkflow` |
| Agent output isn't valid JSON | Formatter agent; raw output saved as an artifact |
| Cursor agents conflict with each other | Tasks run one at a time; small tasks |
| Review/fix loop doesn't end | Maximum 2 rounds, then Project Lead asks you |
| Swarms credits run low | Smaller models for non-critical agents; `max_loops: 1` everywhere |
| Live demo breaks | Pre-recorded video of the full run; live only for the fast path |
| A secret leaks | Push protection on; rotate the key immediately |

---

## 16. Demo script (3 minutes)

| Time | Show |
|---|---|
| 0:00–0:20 | **Problem:** "I have a new idea every day. Turning one into working software takes a team." |
| 0:20–0:40 | **Grok Bot app on your phone:** "Add a daily vocab quiz to the English app." Project Lead answers with the story and asks for approval. You say "Go". |
| 0:40–1:20 | **GitHub issue timeline:** each phase's comment, which swarm type ran and why, `tasks/` created. Cut to Cursor's PR (pre-recorded). |
| 1:20–1:50 | **Review + QA:** Code Review comment, QA Tester's screenshots, Progress Reporter's update in the app. |
| 1:50–2:20 | **Release Vote:** the vote table (show a **HOLD** first: "Security: No-Go, API key in client"), then the fix, then 4/4 Go. You say "Go" and it's merged. |
| 2:20–2:45 | **Live English app** with the new quiz. |
| 2:45–3:00 | **Architecture slide** (FigJam board): Swarms is the brain, Cursor the hands, Grok Bot the voice and eyes. "We built new features of this demo app by talking to Grok Bot." |

---

## 17. Submission checklist

- [ ] Repo public, with the README explaining the system and linking the FigJam board
- [ ] **Swarms section:** each phase, its swarm type, and why (copy the table from [section 6](#6-swarms-agents-and-phases))
- [ ] **Cursor section:** the orchestrator was built with Cursor Agent (screenshots), and the product code is written by Cursor Cloud Agents
- [ ] **Grok Bot section:** 3 bots, their routines, webhooks, launching Cursor agents, QA by using the app like a person
- [ ] Demo video (3 minutes)
- [ ] Opt in to the **"Make it Legendary with SpaceXSI"** raffle when submitting
- [ ] Rotate keys after judging

---

## 18. Using this plan in Cursor

1. Open `sharkbyte_hackathon` in Cursor.
2. Create `.cursor/rules/orchestrator.mdc` with these basics:
   - Python 3.12, `requests` + `PyGithub` + `python-dotenv`
   - small modules
   - never log or prompt with secrets
   - every agent output ends with a JSON block
   - the orchestrator's own comments never start with `/`
3. In Agent mode, work one block at a time: *"Read @PLAN.md. Implement Block 1 only. Ask me before adding dependencies."*
4. After each block, run the matching check from the "Done when" column, commit and push.
5. Save screenshots of the Cursor chats as you go, for the submission.

---

## 19. Not verified yet

These come from search results, because the official Swarms, xAI and Cursor doc pages could not be opened during planning. The setup tests in [section 12](#12-setup-tests-do-these-first) settle them.

- Swarms: the `role` field, the response shape beyond "text from both agents", and which of `HierarchicalSwarm`, `GroupChat`, `MajorityVoting` the API accepts (S1b). Confirmed by S1: the base URL, the `x-api-key` header, `SequentialWorkflow`, the top-level `task` field, and the Grok model name.
- Grok Bot: routine webhooks and their payload, posting to GitHub, sending screenshots in chat, launching Cursor Cloud Agents and returning the PR link
- Cursor Cloud Agents API: exact endpoint and fields (plan B only)
- Vercel `deployment_status` events for preview and production

---

## Demo product: English learning app

Details to come. Keep the first version tiny, for example one lesson page and a word list, so the live feature demo has something to build on.
