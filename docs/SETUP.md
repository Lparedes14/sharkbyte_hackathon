# Setup guide

Project Lead follows this file. The rule: **the bots do every step they can, and ask you only for what needs you**: signing in, creating keys or tokens, pasting secrets into settings, paying, and approving. When Project Lead needs you, it gives one step at a time, with the exact clicks, and checks the result after you say "done".

You never type GitHub commands or repo names into the chat. You talk normally; Project Lead turns that into issues and commands.

---

## Part 1. First-time setup (once per person)

| # | Step | Who | How |
|---|---|---|---|
| 1 | Accounts | **You** | GitHub, Swarms (API key with credits), Cursor Pro or SuperGrok for Grok Bot, Vercel Hobby. |
| 2 | Home base repo | **You** | On GitHub, open the home base template, click **Use this template**, name it, create it. Send Project Lead the link. Project Lead checks it opens. |
| 3 | The three bots | **You** create the bots; **each bot** creates its own routine | Create Project Lead, Progress Reporter and QA Tester in the Grok Bot app with the instructions in Part 5. Then send each bot its "Message me" routine message (Part 5). |
| 4 | Webhook URLs and keys | **You** | Open each bot's Routines, then Message me, and copy the URL and key. They are secrets, so they never go through chat. |
| 5 | GitHub token | **You** | GitHub, Settings, Developer settings, Fine-grained tokens, Generate. **Repository access: All repositories.** Repository permissions: **Administration, Contents, Issues, Pull requests, Secrets, Workflows: Read and write**; **Actions: Read**. No account permissions. |
| 6 | Secrets in home base | **You** | Home base, Settings, Secrets and variables, Actions: add `SWARMS_API_KEY`, `GH_TOKEN`, and for each bot its URL and key (`PROJECT_LEAD_WEBHOOK`, `PROJECT_LEAD_WEBHOOK_KEY`, `PROGRESS_REPORTER_WEBHOOK`, `PROGRESS_REPORTER_WEBHOOK_KEY`, `QA_TESTER_WEBHOOK`, `QA_TESTER_WEBHOOK_KEY`). Settings must show 8 names. |
| 7 | Cursor | **You** | Cursor dashboard: connect GitHub. Cloud Agents is on by default. Keep **Self-hosted machines** and **Enable my machines** off. |
| 8 | Vercel | **You** | Sign in to Vercel with GitHub so it can see your repos. |
| 9 | Health check | **Project Lead** | Opens an issue in home base called "Health check" and comments `/ping`. When the reply shows **Setup complete ✅**, Project Lead saves the note "Setup complete". Any ❌ row names the step to fix. |

---

## Part 2. Starting a new project

**What you say** (any wording works): "Build it", "Let's make this a project", "Start the habit tracker".

**What Project Lead does:**

1. Proposes a repo name (lowercase, dashes) and asks public or private. Waits for your yes.
2. Comments `/build <name> <public|private>` on the idea's issue in home base.

**What the orchestrator then does by itself** (about 30 seconds):

- creates the repo with a README
- adds the agent workflow and `docs/IDEA.md` (the idea, the score card and your answers)
- copies the 8 secrets
- opens the project issue and adds the repo to `projects.json`
- starts Deep Dive, so the PRD arrives about 2 minutes later

It comments a report on the idea issue and sends Project Lead a `repo_created` webhook.

**What Project Lead does next, in its browser, if it can:**

1. Vercel: **Add New**, then **Project**, import the new repo, then **Deploy**. No build settings are needed until the app exists.
2. Vercel: that project's **Settings**, then **Deployment Protection**: turn **Require Log In** off, so QA Tester can open previews.

If Project Lead cannot do these (for example, it is not signed in to Vercel), it tells you these exact steps.

**Later, when the Design phase picks a database:** the app uses Supabase (Postgres). Creating the Supabase project and copying its URL and keys into the Vercel project's Environment Variables is a step for **you**; Project Lead will tell you when.

---

## Part 3. Things only you can do

- Sign in to any service, and approve sign-in or OAuth screens.
- Create tokens and API keys, and paste secrets into settings pages. Secrets never go in chat or on GitHub.
- Pay for anything.
- Say yes to: creating a repo, approving a PRD or scope, merging, releasing.

---

## Part 4. How to talk to Project Lead

Talk normally. Project Lead finds the project in `projects.json`, picks the repo, opens the issue and posts the command.

| You say | Project Lead does |
|---|---|
| "I have an idea: a habit tracker for students." | New idea not in `projects.json`: opens an Idea Inbox issue in home base (label `idea`) and comments `/score`. |
| "Let's start the English app: vocabulary flashcards by topic that I can track every day." | The project is in `projects.json` but has no `docs/PRD.md` yet: opens a project issue in its repo with your words and comments `/run discovery`. |
| "Build it." (after an idea was scored) | Part 2. |
| "Go." / "Yes." (when it asked for approval) | Comments `/approve`. |
| "Make the quiz shorter." (when it asked for approval) | Comments `/revise "make the quiz shorter"`. |
| "Is everything working?" | Comments `/ping` on the "Health check" issue in home base. |

---

## Part 5. Bot instructions

### Project Lead: standing instructions

```text
These are your standing instructions. They replace the earlier ones. Don't create a template or share anything.

You are Project Lead. You help me turn ideas into working software with my agentic build system. Home base: https://github.com/Lparedes14/sharkbyte_hackathon. I only talk to you, and I talk normally; you turn what I say into GitHub issues and commands.

How you work:
- Do every step you can yourself: GitHub pages, issues, comments, and Vercel clicks in your browser. Ask me only for what needs me: signing in, creating tokens or keys, pasting secrets into settings, paying, and approving. When you need me, give one step at a time with the exact clicks, and check the result after I say "done".
- Setup: if you have no note saying "Setup complete", read docs/SETUP.md in home base and walk me through Part 1.
- When I talk about an idea or a project, read projects.json in home base:
  - The project is listed and its repo has no docs/PRD.md yet: open an issue in that repo with my words as the description and comment "/run discovery".
  - The project is listed and already has a PRD: tell me feature work is not built yet.
  - It is a new idea: open an issue in home base with the label "idea", my words as the description, and comment "/score".
- When I say to build an idea: propose a repo name (lowercase, dashes), ask public or private, and after my yes comment "/build <name> <public|private>" on the idea's issue.
- When a webhook arrives, read its "event":
  - approval_needed: open the link, summarize it in 3-5 short lines, and ask me exactly the question. "Go" or "yes" means comment "/approve"; anything else means comment /revise "<my words>".
  - repo_created: follow docs/SETUP.md Part 2 (Vercel import, then turn off Require Log In). If you can't, tell me those exact steps.
  - ping: tell me "Webhook works" and the summary.
  - anything else: tell me the summary and the link.
- Never create a repo, merge, or release without my explicit yes in this chat. Never paste secrets, tokens or keys in chat or on GitHub.
- Commands you may post: /score, /build, /run discovery, /approve, /revise, /ping.
- Keep messages short and always include the link.
```

### Project Lead: update its "Message me" routine

```text
Update the "Message me" routine so it follows your standing instructions for every webhook event: approval_needed, repo_created (do the Vercel steps from docs/SETUP.md Part 2 yourself, or tell me the exact steps), ping, and anything else.
```

### Progress Reporter and QA Tester

Their standing instructions and routines are in `PLAN.md` section 4 and in `CONTEXT.md`.
