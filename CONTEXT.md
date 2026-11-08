# Project Context

Hand-off file for any new chat or for Cursor. It summarizes everything decided, tested and built so far. For the full design, read `PLAN.md`. Where the two disagree, this file has the latest decisions.

Last updated: after Block 1 passed. All setup tests (S1 to S7) are done, and `/ping` on GitHub returns "Setup complete ✅".

---

## 1. The goal in one paragraph

A solo builder (Luis) is in a 48-hour hackathon that has already started. He is building a system where he **talks to a Grok Bot about an idea, and a team of AI agents turns it into a tested, deployed app**. A Swarms API team plans it, Cursor Cloud Agents write the code, Grok Bot talks to him and tests the live app like a real user, and nothing ships without his approval at defined gates. It is for himself (he has a new idea every day), for hackathon teams, and for non-technical founders.

## 2. Prizes being targeted

| Prize | What it requires | Prize |
|---|---|---|
| **Best Use of Swarms API** | Build an agentic workflow using the Swarms API | 1st: interview with the CEO + $1000 credits. 2nd: $750 credits. 3rd: $250 credits. |
| **MLH "Build Your Hackathon A-Team with SpaceXSI"** raffle | Use **Cursor** as the core AI coding agent. Integrate a **Grok Bot** automation into the workflow. Describe in the project description how both are used. Opt in to "Make it Legendary with SpaceXSI" when submitting. | One winning team: a custom-branded Cursor mechanical keyboard for every member |

The Swarms prize is the main target, so **every agent that thinks must run in Swarms**. Grok Bot is the voice and the eyes. It must not take over the reasoning.

## 3. The user and working agreements

- Solo, 48 hours, Python, has Pro accounts for Grok Bot, Grok and Cursor, and a Swarms API key with credits.
- **Reply in English** unless he asks for another language.
- He wants **no space or launch theme**. Use plain, normal names.
- No UI for now. The interface is the Grok Bot app, GitHub and screenshots.
- Approval gates are required. Decisions go through a human in Grok Bot.
- **Cursor writes the code.** He builds `orchestrator/` himself in Cursor's Agent mode. This keeps the "Cursor as core coding agent" claim true. Claude Code in the cloud only writes planning docs, prompts and diagrams. Do not write the orchestrator code for him unless he asks. **Update:** he decided that Claude Code writes all the orchestrator code (Block 1 onward), because his Cursor tokens are limited. Cursor Cloud Agents still write all the product code (the English app) through Project Lead. State this split accurately in the submission.
- Never ask him to paste secrets into a chat. Keys live in `.env` (gitignored) locally and in GitHub Actions secrets.
- Keep Cursor's **Self-hosted machines** and **Enable my machines** settings off, so Cloud Agents run in Cursor's cloud and never on his laptop, where `.env` lives.
- **Talking to Project Lead is conversational.** He never names repos, issues or commands; Project Lead maps what he says to the right repo (through `projects.json`), issue and command (`docs/SETUP.md` Part 4). Any test prompt given to him must be plain conversation too.
- **Bots do what they can; humans only do what needs them** (sign-ins, tokens and keys, pasting secrets, payments, approvals). `docs/SETUP.md` marks who does each step, and Project Lead follows it.
- Keep answers short and practical. Ask before irreversible actions (creating repos, merging, deleting).

## 4. How the idea evolved (and what to avoid reusing)

| Earlier | Now |
|---|---|
| "Mission Control" space theme, Launch Director, Mission Reporter, QA Pilot, "Go/No-Go" | **Project Lead, Progress Reporter, QA Tester, Release Vote, project issue.** The theme was dropped. |
| Orchestrator code in the product repo | Orchestrator code lives **only in `sharkbyte_hackathon`** (home base). Each project repo has a thin trigger workflow that checks out home base at run time. |
| Slack as a chat channel | Not part of the core. Stretch only ("team mode"). The Launch Director talks to him in the **Grok Bot app**. |
| Model `grok-4` | **Returns 404.** Use `openrouter/x-ai/grok-4.3`. |
| One "mission issue" per idea in one repo | **One repo per project.** Ideas wait in an Idea Inbox issue in home base until he approves creating a repo. |

## 5. The architecture

```
You (Grok Bot app) ──► Project Lead ──► posts a command on a GitHub issue
        GitHub Actions starts orchestrator.py (Python)
        Swarms API runs the right team of agents
        results saved in the repo + summary comment on the issue
        webhook ──► Project Lead asks you "Approve?" ──► you say "Go"
        Project Lead launches Cursor Cloud Agents ──► PRs with real code
        Swarms reviews the PR ─► Vercel preview ─► QA Tester tests it ─► Release Vote
        you say "Go" ──► merged and deployed ──► screenshots to you
```

| Tool | Role | Why |
|---|---|---|
| **Swarms API** | The brain: all agents that think, plan, review, vote | Agents only return text. They cannot edit files or run code. |
| **Cursor Cloud Agents** | The hands: write code, run it, fix it, open PRs | They have their own machine. |
| **Grok Bot** | The voice and eyes: chat, approvals, clicking through the live app, screenshots | Works on its own cloud computer like a person. |
| **GitHub Actions** | Runs `orchestrator.py` | A temporary Linux machine per run. Free for public repos (2,000 min/month for private). The orchestrator has no memory between runs. The repo, issues and labels are the memory. |
| **Vercel (Hobby)** | Preview and production deploys of the product | Free. |

**Rule: agents decide, code acts.** A Swarms agent can say "merge PR #3 with squash". `orchestrator.py` is what calls the GitHub API, and only after his approval.

## 6. Repositories

- **Home base: `sharkbyte_hackathon`** (public during the hackathon, private afterwards). Holds `PLAN.md`, `CONTEXT.md`, `projects.json`, `orchestrator/`, `template/`, the Idea Inbox, and `home.yml`. Branch for current work: `claude/nice-planck-4ptghj`. Remote: `https://github.com/Lparedes14/sharkbyte_hackathon`.
- **One repo per project**, created by a "create project" workflow after he approves the name and visibility. The first demo product is an **English-learning app** in its own new repo (`english-app`). He will send the details later. Keep the first version tiny.
- Full folder layout: `PLAN.md`, section 3.

**Rule for ideas:**
- Related to an existing project → a feature issue in that repo.
- New → Idea Inbox issue in home base, with no repo yet.
- A repo is created only after he says "build it" and approves the name and visibility.

## 7. Grok Bot: the three bots

All three live in the Grok Bot app. He only talks to **Project Lead**.

| Bot | Job |
|---|---|
| **Project Lead** | Runs first-time setup. Captures ideas. Asks him the questions the agents generate. Collects approvals. Posts commands on GitHub. Launches Cursor Cloud Agents. Connects new repos to Vercel. |
| **Progress Reporter** | Sends him GitHub activity (PRs, reviews, merges, deploys) with screenshots of the live app and PR pages. Read-only. |
| **QA Tester** | Tests each Vercel preview against `docs/ACCEPTANCE.md`, posts a `QA RESULT` comment with screenshots, files bugs, then posts `/vote`. |

**First-time setup** is Project Lead's first routine. It walks a new user through: accounts, home base repo, the other two bots (copy 3 webhook URLs), a fine-grained GitHub token, 5 Actions secrets, Cursor (GitHub connected, Grok Bot Cloud Agents on), Vercel, then a `/ping` health check. See `PLAN.md` section 5.

Draft instructions for each bot are in `PLAN.md` section 4.

## 8. Swarms phases and agents

| Phase | Agents | Swarm type | Gate |
|---|---|---|---|
| Idea Lab | Idea Scout, Market Researcher, Feasibility Analyst, MVP Cutter | `ConcurrentWorkflow` | — |
| Deep Dive | Product Owner (leads), Product Manager, UX Researcher | `HierarchicalSwarm` | Approve PRD |
| Design | Architect, UX/UI Designer, Security Reviewer, MVP Cutter | `GroupChat` | Approve scope |
| Plan | Tech Lead → Cursor Prompt Writer | `SequentialWorkflow` | — |
| Feature story (fast path) | Product Owner → MVP Cutter | `SequentialWorkflow` | Approve story |
| Code Review | Code Reviewer, Security Reviewer | `ConcurrentWorkflow` | — |
| Release Vote | QA Analyst, Code Reviewer, Security Reviewer, Product Owner | `MajorityVoting` | His final "Go" |
| Release | PR & Merge Manager → DevOps/Release → Docs & Pitch Writer | `SequentialWorkflow` | — |
| Status | Scrum Master | single agent | — |
| Bug triage (stretch) | Bug Triage Router → specialist | `MultiAgentRouter` | — |

Each agent's job and the JSON output contract are in `PLAN.md` section 6. Every phase ends with a fenced JSON block. A Formatter agent repairs bad output.

## 9. Commands and state

Commands are GitHub issue/PR comments that start with `/`. Only the repo owner can trigger them. The orchestrator's own comments never start with `/`.

- Home base: `/score`, `/build <repo-name> public|private`, `/ping`, `/status`
- Project repo: `/run discovery`, `/run feature`, `/approve`, `/revise "<feedback>"`, `/vote`, `/release`, `/status`
- State is stored as labels: `phase:*`, `status:*`, `task:NNN`, `review:*`, `qa:*`, `vote:*`.

## 10. Credentials

| Credential | Where it lives |
|---|---|
| `SWARMS_API_KEY`, `GH_TOKEN` (fine-grained), 3 Grok Bot webhook URLs plus one key per webhook (sent as `Authorization: Bearer <key>`, stored as `*_WEBHOOK_KEY`) | GitHub Actions secrets in home base, copied into each project repo on creation |
| `CURSOR_API_KEY` (plan B only) | Actions secret |
| `VERCEL_TOKEN` (one per account, covers every project) | Home base Actions secret only, never copied to project repos. `/build` uses it to create each repo's Vercel project and turn off Require Log In. |
| His GitHub login for the bots | Grok Bot secure handoff, never in chat |
| App keys | Vercel environment variables, plus Cursor cloud agent secrets for tests |
| Local copy | `.env` (in `.gitignore`), plus `.env.example` with names only |

Never put secrets in Swarms prompts, because agent output is committed to a public repo. Turn on secret scanning with push protection. Rotate all keys after the hackathon.

## 11. Code rules for the orchestrator

- Python 3.12. Libraries: `requests`, `PyGithub`, `python-dotenv`. Use raw `requests` for Swarms (not the SDK, whose method names changed between versions).
- Pass user text through `env:` or the event file. Never put `${{ }}` inside a `run:` command.
- Use `GITHUB_TOKEN` for comments and labels in the current repo. Use `GH_TOKEN` only for creating repos, copying secrets, merging, and reading home base.
- One `concurrency` group per issue or PR. Swarms calls get a timeout (about 10 minutes), 2 retries, and the raw response saved as an artifact.
- Never log secrets.
- **Swarms model:** `openrouter/x-ai/grok-4.20` (set `SWARMS_MODEL` to change it). `grok-4.3` is too slow, and the "fast" `xai/` and `oci/` Grok names returned no usable JSON.
- **Swarms 30-second gateway limit:** `/v1/swarm/completions` answers 503 "Service Unavailable" after about 30 s, but the swarm keeps running and its result is stored. `swarms_client.py` gives each call a unique swarm name and, after a slow 503, polls `/v1/account/logs` for that name and fetches the result with `GET /v1/job/{job_id}` (no re-run, no double billing). Quick 502/503/504 answers are retried. `stream: true` does not help: the gateway buffers the stream and still cuts it at 30 s, and streamed jobs are stored without their output.

## 12. What has been done

1. **Idea refinement** through several rounds: split into brain, hands and eyes; chose swarm types per phase; chose the three bots; chose GitHub Actions as the runner; chose one repo per project.
2. **FigJam board** with 5 diagrams: https://www.figma.com/board/dJnSw0KY8UYIcxjXPz5bcq
   - System Map, Add-a-Feature sequence, First-Time Setup, New Idea to New Repo, Credentials Map.
   - The rendered layout was not checked visually. Fix any layout issues in FigJam.
3. **`PLAN.md`** with the full build plan: components, repos, bots, setup, phases, orchestrator, commands, flows, Cursor handoff, credentials, setup tests S1–S7, timeline, scope, risks, demo script, submission checklist.
4. **Local environment** instructions given: install Git, Python 3.12, Cursor, GitHub CLI; clone; venv; `.gitignore`; `.env`.
5. **S1 (Swarms hello world): passed.** Written by Cursor as `tests/s1_swarms_hello.py`.
   - HTTP 200 with text from both agents, using `SequentialWorkflow` at `POST https://api.swarms.world/v1/swarm/completions` with an `x-api-key` header.
   - `grok-4` returned 404. The fallback came from `GET /v1/models/available`: **`openrouter/x-ai/grok-4.3` works**.
   - **The request body needs a top-level `task` field.**
   - Saved to `tests/s1_request.json` and `tests/s1_response.json`, with no key in either. Those files exist locally. Whether they are pushed to the remote has not been confirmed.
6. **S1b: passed.** `HierarchicalSwarm` (2 agents), `GroupChat` (3 agents) and `MajorityVoting` (3 agents) each returned HTTP 200 with the S1 request shape and `openrouter/x-ai/grok-4.3`. Script: `tests/s1b_swarm_types.py`, with no keys written to disk. HTTP 200 shows the API accepts these swarm types. The output text was not checked in the summary.
7. **S2 (Grok Bot webhook): passed.** Project Lead has a routine called **"Message me"** with a webhook trigger. A `POST` with a JSON body returned HTTP 200 (`{"success":true,"runUuid":...}`) and Project Lead messaged "Webhook works" and the summary in the Grok Bot app. Script: `tests/s2_webhook.py`.
   - Each webhook has a **URL and a key**. Send the key as `Authorization: Bearer <key>`. Without the header the request returns 401.
   - A 200 means the run started. The bot's message arrives a moment later.
   - One routine handles every event by reading the payload's `event` field (`ping` and `approval_needed` are set up; the other events come after S3 and S4).
   - Local `.env` names: `PROJECT_LEAD_WEBHOOK` (URL), `PROJECT_LEAD_WEBHOOK_KEY` (stored as `Bearer <key>`) and `PROJECT_LEAD_WEBHOOK_HEADER` (`Authorization`).
8. **S3 (Grok Bot posts to GitHub): passed.** Project Lead signed in to GitHub and, in `https://github.com/Lparedes14/test_shark_byte`, created issue #1 "S3 test" and the comment "hello from Project Lead".
   - Both appear under the owner's login (`Lparedes14`, labeled Owner). That passes the orchestrator's "only the repo owner can run commands" check.
   - GitHub labels the comment "with Cursor", so bot actions are attributed through Cursor's integration. The login is still the owner's.
9. **S4 (Grok Bot launches a Cursor Cloud Agent): passed.** Project Lead started a Cloud Agent on `Lparedes14/test_shark_byte` and returned the PR link. PR #2 "[task-001] Health page" (branch `cursor/health-page-f3e7`, 2 files, +70) adds a small Python standard-library server with `GET /health` returning `ok`. The agent ran 2 unit tests and a live request (HTTP 200, body `ok`), and put that evidence in the PR description.
   - It worked on a personal Premium account. The Cloud Agents page (`grok.com/dashboard/cloud-agents`) has no on/off toggle for Cloud Agents. Keep **Self-hosted machines** and **Enable my machines** off.
   - The repo needed a first commit on `main` (a README). An empty repo has no branch to start from, so the create-project workflow must create new repos with a README.
   - The PR description appears under the owner's login. GitHub shows 0 checks, since no workflow exists in that repo yet.
   - Not tested: the "Part of #<issue number>" line in the PR description, and `.cursor/rules` plus a task file as input. The S4 prompt did not include them.
10. **S5 (Progress Reporter sends a screenshot): passed.** A second bot, **Progress Reporter**, opened `https://github.com/Lparedes14/test_shark_byte/pull/2`, summarized the PR in one line, and sent a screenshot of the page in the Grok Bot app. It said it made no changes on GitHub, which matches its read-only instructions.
   - Progress Reporter does not have its own webhook routine yet. It needs one before the orchestrator can notify it (`PROGRESS_REPORTER_WEBHOOK` and `PROGRESS_REPORTER_WEBHOOK_KEY`).
11. **S6 (Vercel preview): passed, with changes to the plan.** Imported `test_shark_byte` in Vercel (Hobby, preset Other, no build settings). PR #3 "[task-002] Static page" (adds `index.html`; opened by a Cloud Agent through Project Lead; description says "Part of #1") got a Vercel preview that serves "Hello from test_shark_byte".
   - Vercel reports with a commit status named `Vercel`, a `Vercel Preview Comments` check, and a comment from `vercel[bot]`. The repo has **no GitHub Deployments**, so **no `deployment_status` event fires**. Use the `status` event (context `Vercel`, state success) and read the preview URL from the bot's PR comment. The comment is `[vc]: #<hash>:<base64>`, and the base64 decodes to JSON with `projects[].previewUrl`. Neither is tested inside a workflow yet.
   - Previews were behind Vercel Authentication (a redirect to a login page), which would block QA Tester. He turned off **Require Log In** in the project's Settings > Deployment Protection. Previews are now public to anyone with the URL. For a real product, use Protection Bypass for Automation instead.
   - Cloud Agents add the "Part of #<issue>" line when the prompt asks for it.
12. **S7 (GitHub Actions answers `/ping`): passed.** `.github/workflows/s7-ping.yml` in `sharkbyte_hackathon` runs on `issue_comment`. About a minute after he commented `/ping` on issue #1, `github-actions[bot]` replied "pong - the workflow ran".
   - The first version failed with "error in your yaml syntax": an unquoted `run:` value contained `: `. Put shell commands in a `run: |` block and keep `: ` out of unquoted values. A broken workflow file shows up as a failed `push` run with 0 jobs, and the workflow is listed by its file path instead of its `name`.
   - `gh` has no checkout in the job, so pass `--repo "$GITHUB_REPOSITORY"`.
   - The owner check (`github.event.comment.user.login == github.repository_owner`) and `startsWith(..., '/ping')` worked. `issue_comment` workflows run from the default branch (`claude/nice-planck-4ptghj`), and an old comment does not re-run after a fix.
   - The reply comes from `GITHUB_TOKEN`, so it does not trigger another run.

## 13. What is not done yet (next steps, in order)

1. **S1b: done** (see section 12).
2. **S2: done** (see section 12).
3. **S3: done** (see section 12).
4. **S4: done** (see section 12).
5. **S5: done** (see section 12).
6. **S6: done** (see section 12). The trigger is the `status` event, not `deployment_status`.
7. **S7: done** (see section 12).
8. **Block 1 (skeleton):** repo layout, `requirements.txt`, secrets, `home.yml`, `/ping` round trip → "Setup complete". **Code written and tested locally** (`orchestrator/main.py`, `health.py`, `notify.py`, `github_io.py`, `swarms_client.py`, and `.github/workflows/home.yml`, which replaces the S7 test workflow). **Block 1 is done:** all three bots have a "Message me" webhook routine, the 8 Actions secrets are set in home base, and a `/ping` comment on issue #1 returned "Setup complete ✅" (Swarms key, GitHub token and all three webhooks answered). Note: the `GH_TOKEN` fine-grained token needed **All repositories** access (not "Public repositories") for its write permissions to apply.
8b. **Block 2 (Idea Lab + Deep Dive): code written, tested locally against the real Swarms API, not yet run on GitHub.**
   - Files: `orchestrator/parsing.py`, `state.py`, `phases/common.py`, `phases/idea_lab.py`, `phases/discovery.py`, agent specs in `orchestrator/agents/` (`idea_lab.json`, `deep_dive.json`, `formatter.json`), the expanded `github_io.py` and `main.py`, and `template/.github/workflows/agent.yml` (the thin trigger for project repos, with `ORCH_CONTEXT=project`). `home.yml` sets `ORCH_CONTEXT=home`. Both upload `.orchestrator-runs/` (raw Swarms responses) as an artifact.
   - Commands: home base takes `/ping`, `/score`, `/revise`, `/approve`; project repos take `/ping`, `/run discovery`, `/approve`, `/revise "<feedback>"`. `/approve` on a PRD moves the issue to `phase:design` (Design is item 8e).
   - Local results with the English app idea: Idea Lab scored it 6.8/10 in 13 s with 6 open questions; Deep Dive wrote "VocabVida" with 4 user stories and 15 acceptance criteria in 25 s.
   - Local dev commands: `python orchestrator/main.py --local-run idea_lab "<idea>"` and `--local-run discovery "<idea>"` print the result and post nothing.
   - Pushed as `089f3c6`. `test_shark_byte` got `.github/workflows/agent.yml` (`8a25af6`) and the 8 secrets, so it acts as the English app's repo.
8c. **`/build` (create project) and the setup guide: code written and tested offline, not yet run on GitHub.**
   - `orchestrator/build.py`: on an Idea Inbox issue, `/build <name> public|private` creates the repo with a README, copies `template/` and writes `docs/IDEA.md`, copies the 8 secrets (sealed with PyNaCl), opens the project issue, adds the repo to `projects.json` (so `home.yml` now has `contents: write`), and posts `/run discovery` with `GH_TOKEN` so Deep Dive starts. It reports on the idea issue and sends Project Lead a `repo_created` webhook with the Vercel steps.
   - `docs/SETUP.md`: first-time setup, new project, things only the human can do, how to talk to Project Lead, and the new Project Lead instructions.
   - Pushed as `05d2449`.
8d. **Block 1 and Block 2 verified on GitHub (2026-11-07).** `/ping` shows all 7 rows green. The conversational test passed on `test_shark_byte`: "Let's start the English app..." became issue #4, `/run discovery` wrote `docs/PRD.md` and `docs/ACCEPTANCE.md` (VocabDaily, 4 stories, 13 criteria) in 34 s, and "Go" posted `/approve` (`phase:design`). Project Lead also showed the PRD in chat when asked. `/build` is still untested on GitHub.
8e. **Design phase: code written and tested locally against the real Swarms API, not yet run on GitHub.**
   - Files: `orchestrator/phases/design.py`, `orchestrator/agents/design.json` (Architect, UX/UI Designer, Security Reviewer, MVP Cutter; `GroupChat`), `main.py` wiring. `/approve` on the PRD now starts Design by itself (about 1 minute); `/run design` runs it by hand; `/revise "<feedback>"` re-runs it with the old `docs/DESIGN.md` as the base; `/approve` on the design moves the issue to `phase:plan` (Plan is the next block).
   - Output: `docs/DESIGN.md` (stack, pages, data model, API, security rules, env var names, decisions, scope in and out, risks, steps only a human can do, open questions). The design defaults to Supabase (Postgres) with anonymous sign-in and Row Level Security, so the English app keeps its progress across days and devices. The product title always comes from the PRD heading.
   - **Swarms fact learned (GroupChat):** with the swarm-level `max_loops` left at its default, only the first agent spoke. With `"max_loops": 6` and `"list_all_agents": true` all four agents spoke (Architect x2, UX/UI Designer, Security Reviewer, MVP Cutter x2) in 44 s. `swarms_client.load_spec` now passes both swarm-level keys through. The MVP Cutter's last turn is not always valid JSON, so the Formatter fallback turns the debate into the JSON (10 s more). The gateway answered 503 after 31 s and the job-recovery code fetched the result.
   - Local results with the real VocabDaily PRD: 4 stack choices, 2 pages, 4 tables, 5 items left out of scope; the human steps it lists are creating the Supabase project, turning on Anonymous sign-ins, running the migration in the SQL editor and adding the two env var names in Vercel.
   - Dev command: `python orchestrator/main.py --local-run design <PRD file>`.
   - **Vercel, Option B (decided):** `orchestrator/vercel.py` uses one `VERCEL_TOKEN` to create a Vercel project per repo (linked to it) and turn off Require Log In, inside `/build`. Without the token, or if Vercel cannot see the repo, `/build` falls back to the manual Vercel steps for Project Lead. `/ping` has a "Vercel token" row. `docs/SETUP.md` Part 1 now includes the Vercel GitHub app with **All repositories** (step 6), the Vercel token (step 7) and 9 home base secrets (step 8). The Vercel API calls are **not tested yet**; they wait for his token.
   - **Needs from him:** add **Workflows: Read and write** to the `GH_TOKEN` fine-grained token (needed to write the workflow file into new repos), create the Vercel token and add it to `.env` and the home base secrets, and paste the new Project Lead instructions from `docs/SETUP.md` Part 5.
9. **Done:** the three Grok Bot bots exist with their instructions from `PLAN.md` section 4.
10. **Decided:** the English app is the test product from Block 2 on. **Version 1, in his words: vocabulary flashcards by topic that he can track every day.** Keep it tiny and easy to extend; later features come through Project Lead. Its repo for now is `test_shark_byte` (`projects.json` key `english-app`). Its data lives in **Supabase (Postgres)**, the Architect default (Next.js + Supabase on Vercel): the Design phase writes the data model into `docs/DESIGN.md`, Cursor agents write the SQL migrations, and the Supabase keys go in Vercel environment variables. The build system itself needs no database: the repos (issues, labels, `docs/*.md`, PRs) are its memory.
11. Build phases in the order of `PLAN.md` section 13. The cut order if behind: morning digest → bug triage → automatic Vercel import → create project workflow (create the repo by hand) → Design as its own phase.

Fallbacks if a test fails: polling instead of Grok Bot webhooks; the Cursor Cloud Agents API from the orchestrator instead of Grok Bot launching agents; he posts commands himself instead of Grok Bot.

## 14. What is verified and what is not

**Verified by S1 and S1b:** Swarms base URL and `x-api-key`, `SequentialWorkflow`, `HierarchicalSwarm`, `GroupChat` and `MajorityVoting` (all HTTP 200), the `task` field, the Grok model name, and that `/v1/models/available` lists models.

**Verified in Block 2:** every swarm type returns `"output": [{"role": "<agent name>", "content": "<text>"}]`. `ConcurrentWorkflow` gives one entry per agent. `HierarchicalSwarm` adds its own built-in `Director` (and `System` entries) that orders the agents, so the agent we call the director does not automatically go last; the parser skips `System`/`Director` and searches every answer for the JSON. A one-agent `SequentialWorkflow` works (used by the Formatter). The optional `role` field is not needed.

**Not verified.** These came from web search, because the Claude Code cloud session could not open the official Swarms, xAI or Cursor docs pages (the network blocked them). Treat as claims to test:
- Swarms: the `role` field, `MultiAgentRouter` behavior, the output quality of `HierarchicalSwarm`, `GroupChat` and `MajorityVoting` (S1b checked HTTP status only), and response shapes.
- Grok Bot: launched August 2026 as a beta. Bots share one cloud computer with a browser and log into apps like a person. **Skills** are reusable across bots. **Routines** belong to one bot, can be scheduled, and run in the cloud (up to 50 per bot). The official docs page "Skills and routines" mentions webhooks (a 200 response means the run started, not finished), and S2 confirmed they work. Bot-to-bot messaging still needs testing. S3 confirmed that posting to GitHub works, and S5 confirmed that screenshots arrive in chat. Secrets use a secure handoff flow.
- Grok Bot → Cursor: sources say the Cursor dashboard's Grok Bot page has a team-wide **Cloud Agents** toggle (on by default) that lets bots start Cloud Agents, which clone the repo and open a PR. Accounts on Legacy Privacy Mode may need to switch. S4 confirmed that Project Lead can launch a Cloud Agent and return the PR link, on a personal Premium account where the Cloud Agents page has no on/off toggle.
- Cursor Cloud Agents API (plan B): community docs describe `POST /v0/agents` with a prompt and a source repo. Official docs may differ.
- Vercel: S6 showed there are no `deployment_status` events. Still untested: a workflow triggered by the `status` event, parsing the preview URL from the bot comment, and the production deploy after a merge.

## 15. Demo plan

Live demo is the **feature fast path**: he tells Project Lead in the Grok Bot app "Add a daily vocab quiz to the English app". Story and acceptance criteria → he approves → plan → Cursor PR → review → QA Tester screenshots → Release Vote (show a **HOLD** first, then a fix, then all Go) → he says "Go" → merged and live. The full new-idea-to-new-repo flow is shown as a pre-recorded clip. A 3-minute script is in `PLAN.md` section 16.

## 16. Submission checklist (summary)

Public repo with a README that links the FigJam board. A Swarms section (each phase, swarm type and why). A Cursor section (orchestrator built in Cursor Agent, with screenshots; product code written by Cursor Cloud Agents). A Grok Bot section (3 bots, routines, webhooks, Cursor launching, QA through the app). A 3-minute demo video. Opt in to the **"Make it Legendary with SpaceXSI"** raffle. Rotate keys after judging.

## 17. Prompt used for S1b (done, kept for reference)

```text
Read @CONTEXT.md and @PLAN.md section 12 and the S1 result.

Create tests/s1b_swarm_types.py using only requests and python-dotenv.
- Reuse the request shape in tests/s1_request.json (it includes the top-level
  "task" field) and the model openrouter/x-ai/grok-4.3.
- For each swarm_type in HierarchicalSwarm, GroupChat, MajorityVoting: send a
  request with 2 or 3 tiny agents and a one-line task, then print the swarm type,
  HTTP status, and a short preview of the output.
- If a type fails, print the full error body for that type and continue with the
  next one. Don't guess other fields.
- Write one summary table at the end: swarm type, status, a note.
- Don't write any key to disk.

Don't change anything outside tests/.
```
