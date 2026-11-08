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
| 6 | Vercel and its GitHub app | **You** | Sign in to Vercel with GitHub (Hobby plan is free). When Vercel's GitHub app asks which repositories it may see, choose **All repositories**, so it can see every new project repo. To check later: GitHub, Settings, Applications, Vercel, Configure, Repository access. |
| 7 | Vercel token | **You** | Vercel, your avatar, Account Settings, Tokens, **Create Token**. Name `sharkbyte-orchestrator`, scope: your Hobby team, an expiry such as 30 days. Copy it once (Vercel shows it only once). One token covers every project; `/build` uses it to create each project's Vercel project and make its previews public. |
| 8 | Secrets in home base | **You** | Home base, Settings, Secrets and variables, Actions: add `SWARMS_API_KEY`, `GH_TOKEN`, `VERCEL_TOKEN`, and for each bot its URL and key (`PROJECT_LEAD_WEBHOOK`, `PROJECT_LEAD_WEBHOOK_KEY`, `PROGRESS_REPORTER_WEBHOOK`, `PROGRESS_REPORTER_WEBHOOK_KEY`, `QA_TESTER_WEBHOOK`, `QA_TESTER_WEBHOOK_KEY`). Settings must show 9 names. `VERCEL_TOKEN` stays in home base only; project repos never get it. |
| 9 | Cursor | **You** | Cursor dashboard: connect GitHub. Cloud Agents is on by default. Keep **Self-hosted machines** and **Enable my machines** off. |
| 10 | Health check | **Project Lead** | Opens an issue in home base called "Health check" and comments `/ping`. When the reply shows **Setup complete ✅**, Project Lead saves the note "Setup complete". Any ❌ row names the step to fix. |

---

## Part 2. Starting a new project

**What you say** (any wording works): "Build it", "Let's make this a project", "Start the habit tracker".

**What Project Lead does:**

1. Proposes a repo name (lowercase, dashes) and asks public or private. Waits for your yes.
2. Comments `/build <name> <public|private>` on the idea's issue in home base.

**What the orchestrator then does by itself** (about 30 seconds):

- creates the repo with a README
- creates the project's own **Vercel project**, linked to the new repo, with **Require Log In off** so previews are public (one Vercel project per repo, all with the same `VERCEL_TOKEN`)
- adds the agent workflow and `docs/IDEA.md` (the idea, the score card and your answers)
- saves the project's stable production URL in `docs/LINKS.md`, so the bots can find the live app
- copies the 8 secrets the project repo needs (not `VERCEL_TOKEN`)
- opens the project issue and adds the repo to `projects.json`
- starts Deep Dive, so the PRD arrives about 2 minutes later

It comments a report on the idea issue and sends Project Lead a `repo_created` webhook.

**Only if the Vercel step could not run** (no `VERCEL_TOKEN`, or Vercel cannot see the repo), the report and the webhook list these steps. Project Lead does them in its browser if it can; otherwise it tells you these exact steps:

1. Vercel: **Add New**, then **Project**, import the new repo, then **Deploy**. No build settings are needed until the app exists.
2. Vercel: that project's **Settings**, then **Deployment Protection**: turn **Require Log In** off, so QA Tester can open previews.

If the report says Vercel cannot see the repo, fix Part 1 step 6 (the Vercel GitHub app needs **All repositories**).

**When you approve the PRD,** the Design phase starts by itself and writes `docs/DESIGN.md` about a minute later: stack, pages, data model, security rules and scope. Approve it with "Go", or say what to change.

**After the design, the Plan phase** splits it into 3 to 6 small tasks in `tasks/`, plus `.cursor/rules/project.mdc`. You approve the list with "Go"; Cursor then builds one task at a time.

**Building.** After you approve the plan, the orchestrator hands task 001 to Project Lead (a `build_task` webhook that carries the exact prompt), and Project Lead starts a Cursor Cloud Agent. Cursor opens a pull request titled `[task-001] ...`. The orchestrator labels it, comments on the issue and tells Project Lead. You review and merge the PR on GitHub; the merge starts the next task by itself, until all tasks are merged (`phase:done`). Tasks always run one at a time.

**If the design uses Supabase (Postgres), the steps for you are** (Project Lead lists them when the design is ready, and walks you through them when the build needs them): create the Supabase project, turn on **Anonymous sign-ins** (Authentication, Sign In / Providers), run the SQL migration that Cursor writes under `supabase/migrations` in the Supabase SQL editor, and add `NEXT_PUBLIC_SUPABASE_URL` and `NEXT_PUBLIC_SUPABASE_ANON_KEY` in the Vercel project's Environment Variables. Keys never go through chat or GitHub.

---

## Part 3. Things only you can do

- Sign in to any service, and approve sign-in or OAuth screens.
- Create tokens and API keys (Swarms, GitHub, Vercel), and paste secrets into settings pages. Secrets never go in chat or on GitHub.
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
| "Go." (when it showed the design) | Comments `/approve`; the Plan phase starts and writes the task list about 2 minutes later. |
| "Go." (when it showed the plan) | Comments `/approve`; the issue moves to the Build phase and the first task goes to Cursor. |
| "Start the next task." / "Try that task again." | Comments `/next` (or `/next again` to send a task to Cursor again when no PR came). |
| "Redo the design with fewer tables." | Comments `/revise "redo the design with fewer tables"`. |
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
  - approval_needed (a PRD, a design or a plan): open the link, summarize it in 3-5 short lines, and ask me exactly the question. If I ask to see the document, show it here so I do not have to open GitHub. "Go" or "yes" means comment "/approve"; anything else means comment /revise "<my words>".
  - repo_created: tell me the project is ready, with its links. If the summary lists steps that need a browser sign-in, follow docs/SETUP.md Part 2: do them yourself if you can, otherwise tell me the exact steps.
  - build_task: start a Cursor Cloud Agent on the repo in the "repo" field, and give it exactly the text in the "prompt" field as its instructions. Do not change the prompt and do not merge anything. Tell me in one line which task started. When Cursor gives you the pull request link, tell me.
  - pr_opened: tell me in 2-3 lines that Cursor's pull request is ready, with the link. If I ask, open the preview and show me a screenshot. Never merge or approve it yourself; I merge it on GitHub.
  - build_done: tell me all tasks are built and merged.
  - build_failed: tell me the Vercel build failed, with the link, and offer to send the error to Cursor so it fixes the pull request.
  - ping: tell me "Webhook works" and the summary.
  - anything else: tell me the summary and the link.
- Never create a repo, merge, or release without my explicit yes in this chat. Never paste secrets, tokens or keys in chat or on GitHub.
- Commands you may post: /score, /build, /run discovery, /approve, /revise, /next, /ping.
- Keep messages short and always include the link.
```

### Project Lead: update its "Message me" routine

```text
Update the "Message me" routine so it follows your standing instructions for every webhook event: approval_needed, build_task (start a Cursor Cloud Agent with the prompt field, exactly), pr_opened, build_done, repo_created (tell me the project is ready; if the summary lists browser steps, do them yourself from docs/SETUP.md Part 2 or tell me the exact steps), ping, and anything else.
```

### Progress Reporter and QA Tester

Their first standing instructions and routines are in `PLAN.md` section 4 and in `CONTEXT.md`. When Vercel finishes a build for a task PR, the orchestrator sends them the URL by itself (events `preview_ready`, `qa_request` and `production_live`, each with a `preview_url` field). Send each bot its update message once:

**Progress Reporter: update message**

```text
Update your standing instructions and your "Message me" routine. New webhook events carry a preview_url field:
- preview_ready: open preview_url on a desktop-size window and on a phone-size window, send me both screenshots and one line on what you see.
- production_live: do the same for preview_url, which is the live app, and say what changed.
For any other event, keep doing what you do now. You only read and report; never change anything on GitHub.
```

**QA Tester: update message**

```text
Update your standing instructions and your "Message me" routine. When the event is qa_request: open preview_url like a real user and test the acceptance criteria named in the summary (docs/ACCEPTANCE.md in the repo, only the ones the task in the summary delivers). Then add one comment on the pull request in the link field. Its first line is exactly "QA RESULT: PASS" or "QA RESULT: FAIL", followed by one line per criterion with a check or a cross and what you saw. Send me the screenshots and the same summary here. Change nothing else on GitHub.
```
