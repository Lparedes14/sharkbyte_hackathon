# How to set up the three Grok Bot agents (step by step)

This guide is for the hackathon. It tells you how to get the three bots that run this system, how to connect them to the orchestrator, how to test each connection, and what to do when something goes wrong. You do not need to know anything about webhooks. Follow the steps in order and do each check.

**Time:** about 45 minutes the first time. **Cost:** you need a Grok Bot plan (SuperGrok or Cursor Pro, as in `SETUP.md` Part 1).

---

## 0. What you are building

Three bots live in the Grok Bot app. They are the "face" of the system: you talk to one of them, and the other two report and test.

| Bot | Its job in one sentence | You talk to it? |
|---|---|---|
| **Project Lead** | Your only conversation partner. It turns what you say into GitHub issues and commands, asks you for approvals, and starts Cursor Cloud Agents to write the code. | **Yes, all the time** |
| **Progress Reporter** | Opens the preview or live app, takes desktop and phone screenshots, and sends you a short update. It only reads, it never changes anything. | Sometimes ("show me the app") |
| **QA Tester** | Opens each preview like a real user, checks the acceptance criteria, and writes one `QA RESULT: PASS` or `FAIL` comment on the pull request. | No, it works by itself |

How they get their work: the **orchestrator** (the Python code in this repo, run by GitHub Actions) sends each bot a small message called a **webhook**. A webhook is just a web address (URL) plus a secret key. When the orchestrator "calls" it, the bot wakes up, reads the message, and does its job. That is why each bot needs a **routine called "Message me"** with a webhook trigger.

```
You  <--chat-->  Project Lead  --comments /commands-->  GitHub  --Actions-->  orchestrator (Swarms agents)
                      ^                                                              |
                      |  webhook "Message me"  <-------------------------------------+
Progress Reporter <---+  (screenshots)          <-- webhook ---------------------------+
QA Tester         <---+  (tests the preview)    <-- webhook ---------------------------+
```

---

## 1. Before you start (checklist)

Tick every line. If one is missing, do `SETUP.md` Part 1 first.

- [ ] You have a GitHub account and your own copy of this repo (your **home base**).
- [ ] You have the Grok Bot app open and you are signed in.
- [ ] You have a Swarms API key with credits, a GitHub token, and (for new projects) a Vercel token. These go in `.env` and in GitHub secrets (Step 6).
- [ ] You have Python 3.12 and have run `pip install -r requirements.txt` (only needed for the test commands).

**Golden rule for the whole guide:** never paste a key, token or password into a chat, a GitHub comment, an issue or a screenshot. If a bot asks you for a secret in chat, stop and use its secure handoff instead.

---

## 2. Step 1: Add the three bots to your Grok Bot

Each bot has a share link. Open it, read the page, and click **Add to Grok Bot**.

| Bot | Share link |
|---|---|
| **Project Lead** | https://x.ai/bot/egDXuf_4KO1c8LnAUNbbl |
| **Progress Reporter** | https://x.ai/bot/tXR4LtstF90Dkx33p0yqA |
| **QA Tester** | https://x.ai/bot/NEcmLsDFXM35i7mVwiOEZ |

What you will see on each page: the bot's name, "by Luis", a one-line description, and this warning: *"This AI bot was created by a third-party user, not by SpaceXSI. It may act on your behalf."* That is true and important: a bot signs in to GitHub **as you**, so its comments appear under your name. That is by design (it is how it posts commands), and it is also why you should read each bot's instructions (Step 2) before you trust it.

**Check:** the three bots now appear in the left sidebar of Grok Bot under **Bots**: Project Lead, Progress Reporter, QA Tester.

> **Important:** a share link copies the bot, not your secrets. Your webhook URLs and keys belong to your account, so **no share link can carry them**. You always create them yourself in Step 4. If a bot looks empty after you add it, you are not stuck: Step 2 gives you all the instructions to paste.

---

## 3. Step 2: Check (or paste) each bot's instructions

Open each bot, open its settings (instructions), and compare with the text below. If it is empty or different, delete it and paste the text from the box. Instructions are the bot's job description, so this is the most important step.

> **Before you paste Project Lead's text:** replace `<YOUR-HOME-BASE-URL>` with the address of **your** repo, for example `https://github.com/yourname/sharkbyte_hackathon`.

### 2.1 Project Lead

```text
You are Project Lead. You help me turn ideas into working software with my agentic build system. Home base: <YOUR-HOME-BASE-URL>. I only talk to you, and I talk normally; you turn what I say into GitHub issues and commands.

How you work:
- Do every step you can yourself: GitHub pages, issues, comments, and Vercel clicks in your browser. Ask me only for what needs me: signing in, creating tokens or keys, pasting secrets into settings, paying, and approving. When you need me, give one step at a time with the exact clicks, and check the result after I say "done".
- Setup: if you have no note saying "Setup complete", read docs/SETUP.md and docs/HOWTO-GROK-BOTS.md in home base and walk me through them.
- When I talk about an idea or a project, read projects.json in home base:
  - The project is listed and its repo has no docs/PRD.md yet: open an issue in that repo with my words as the description and comment "/run discovery".
  - The project is listed and already has a PRD (a new feature for an existing product): open an issue in that repo with my words as the description and comment "/run feature". When the feature story arrives, summarize it and ask for Go like a PRD; after Go the plan arrives, ask for Go again.
  - It is a new idea: open an issue in home base with the label "idea", my words as the description, and comment "/score".
- When I say to build an idea: propose a repo name (lowercase, dashes), ask public or private, and after my yes comment "/build <name> <public|private>" on the idea's issue.
- When a webhook arrives, read its "event":
  - approval_needed (a PRD, a design or a plan): open the link, summarize it in 3-5 short lines, and ask me exactly the question. If I ask to see the document, show it here so I do not have to open GitHub. "Go" or "yes" means comment "/approve"; anything else means comment /revise "<my words>".
  - repo_created: tell me the project is ready, with its links. If the summary lists steps that need a browser sign-in, follow docs/SETUP.md Part 2: do them yourself if you can, otherwise tell me the exact steps.
  - build_task: start a Cursor Cloud Agent on the repo in the "repo" field, and give it exactly the text in the "prompt" field as its instructions. Do not change the prompt and do not merge anything. Tell me in one line which task started. When Cursor gives you the pull request link, tell me.
  - pr_opened: tell me in 2-3 lines that Cursor's pull request is ready, with the link. If I ask, open the preview and show me a screenshot. Never merge or approve it yourself; the system reviews and tests it and then asks me for a Go.
  - changes_requested: if the payload has a "prompt" field, send exactly that text as a follow-up to the Cursor agent that opened the pull request in the link field (the same agent), tell me in one line, and do not merge anything. If it has no prompt field, tell me the summary and ask me what to do: ask Cursor again, release anyway, or close the PR. Do nothing until I answer.
  - vote_result: summarize the release vote in 2-3 short lines with the pull request link, and ask me the question. If I answer Go or yes, comment exactly "/release" on that pull request. If a HOLD happened and I say to release anyway, comment "/release anyway". Never post /release without my explicit yes in this chat.
  - merged: tell me the pull request is merged and going live, with the link.
  - build_done: tell me all tasks are built and merged.
  - build_failed: tell me the Vercel build failed, with the link, and offer to send the error to Cursor so it fixes the pull request.
  - ping: tell me "Webhook works" and the summary.
  - anything else: tell me the summary and the link.
- Never create a repo, merge, or release without my explicit yes in this chat. Never paste secrets, tokens or keys in chat or on GitHub.
- Commands you may post: /score, /build, /run discovery, /run feature, /approve, /revise, /next, /release (only after my Go), /ping. QA Tester's report starts the vote by itself, so you never post /vote.
- Keep messages short and always include the link.
```

### 2.2 Progress Reporter

```text
You are Progress Reporter. You only read and report. You never change anything on GitHub, Vercel or Cursor.

When a webhook arrives, read its "event" and open the links in it. Some events carry a "preview_url" field.
- preview_ready: open preview_url in a desktop-size window and then in a phone-size window. Send me both screenshots and one line on what you see.
- production_live: do the same for preview_url, which is the live app, and say what changed.
- Any other event (pull request opened, merged, build done, ping): send me a 2-3 line update with the link. Take a screenshot of the page only if it helps.

If I ask "show me the app", open the latest preview or production URL from the most recent update and send screenshots.
Keep messages short and always include the link.
```

### 2.3 QA Tester

```text
You are QA Tester. You test previews like a real user, and you report on the pull request.

When a webhook arrives with the event qa_request:
1. Open preview_url in a browser.
2. Read the acceptance criteria: the task file named in the summary (tasks/NNN-*.md in the repo) and docs/ACCEPTANCE.md. Test only the criteria that this task delivers.
3. Test each criterion on the preview like a real user and take a screenshot for each one.
4. Post exactly ONE comment on the pull request in the "link" field. Its first line must be exactly "QA RESULT: PASS" or "QA RESULT: FAIL". Then one line per criterion, starting with [x] if it works or [ ] if not, and what you saw. For a failed criterion add the steps to reproduce it.
5. Send me the screenshots and the same summary here.

Do not post /vote (the system starts the release vote by itself from your result). Do not open issues. Do not change anything else on GitHub.
For any other event (ping and so on), just tell me the summary.
```

**Check:** in each bot, you can see the instructions you just pasted.

---

## 4. Step 3: Let each bot sign in to GitHub

Project Lead and QA Tester post comments on GitHub, and Progress Reporter opens PR pages. They do it in their own browser inside Grok Bot, and they use **your** GitHub login.

1. Open **Project Lead** and send: `Open <YOUR-HOME-BASE-URL> and tell me the name of the repo.`
2. If it needs you to sign in, it will tell you. Sign in yourself on the page it shows. **Type your password only on GitHub's own page, never in the chat.**
3. Repeat for **QA Tester** and **Progress Reporter** if they ask.

**Check:** the bot answers with the repo name. If it says it cannot open the page, finish the sign-in it asked for and ask again.

---

## 5. Step 4: Create the "Message me" routine in each bot

This is the step that connects each bot to the orchestrator. Do it **once per bot** (three times).

1. Open the bot's chat and send this message exactly:

```text
Create a routine called "Message me". Its trigger is a webhook. When the webhook is called, read the JSON body (fields: event, repo, link, summary, question, preview_url, prompt) and follow your standing instructions for that event. When it is created, give me the webhook URL, the key, and the header name through the secure handoff you use for secrets.
```

2. The bot creates the routine and gives you **three things**: the **webhook URL**, the **key**, and the **header name** (normally `Authorization`). The key is sent as `Authorization: Bearer <key>`; the code adds the word `Bearer` for you if you leave it out.
3. Copy them into a safe place (Step 5). **Do not** put them in chat, in a GitHub comment, or in a screenshot.
4. You can see the routine again later: open the bot, then **Routines**, then **Message me**.

**Check:** the routine "Message me" shows in the bot's Routines list, with a webhook trigger.

> **Why a routine and not just chat?** The orchestrator runs on GitHub's servers and cannot type into your chat. A webhook is the door it can knock on. A reply of **HTTP 200** from that door means "the bot started its run".

---

## 6. Step 5: Put the URLs and keys where the code can read them

You store the **same six values** in two places: your local `.env` file (to test from your computer) and your home base's GitHub secrets (so GitHub Actions can use them).

| Bot | Variable for the URL | Variable for the key |
|---|---|---|
| Project Lead | `PROJECT_LEAD_WEBHOOK` | `PROJECT_LEAD_WEBHOOK_KEY` |
| Progress Reporter | `PROGRESS_REPORTER_WEBHOOK` | `PROGRESS_REPORTER_WEBHOOK_KEY` |
| QA Tester | `QA_TESTER_WEBHOOK` | `QA_TESTER_WEBHOOK_KEY` |

**A. Local `.env`** (only on your computer; git ignores it):
1. Copy `.env.example` to `.env`.
2. Fill in the six lines above. Only if a bot gave you a header name other than `Authorization`, also add `<BOT>_WEBHOOK_HEADER=thatname`.
3. Never commit `.env` and never screenshot it.

**B. GitHub secrets** (so Actions can call the bots):
1. Open your home base on GitHub, then **Settings**, **Secrets and variables**, **Actions**, **New repository secret**.
2. Create one secret per variable, with the same names. In total the home base needs these **9 secrets**: the six above plus `SWARMS_API_KEY`, `GH_TOKEN` and `VERCEL_TOKEN` (see `SETUP.md` Part 1, steps 5 to 8).
3. You never copy secrets to a project repo by hand: `/build` copies the eight that a project needs, by itself.

**Check:** Settings shows 9 secret names. (GitHub never shows the values again, which is normal.)

---

## 7. Step 6: Test each bot's webhook (one command)

From the repo root:

```bash
python tests/webhook_test.py all
```

What you should see:

```text
ok   project_lead: HTTP 200
ok   progress_reporter: HTTP 200
ok   qa_tester: HTTP 200
```

Then open the Grok Bot app: **each bot should have sent you a message** like "Webhook works" with the test summary. You can also test one bot at a time: `python tests/webhook_test.py qa_tester`.

| If you see | It means | Do this |
|---|---|---|
| `HTTP 200` but no message in the app | The routine started but the bot has no instruction for "ping" | Re-paste its instructions (Step 2) and send the Step 4 message again |
| `FAIL ... HTTP 401` | The key or header is wrong | Re-check `<BOT>_WEBHOOK_KEY` in `.env`. Keys are case-sensitive. If the bot gave a header other than `Authorization`, set `<BOT>_WEBHOOK_HEADER` |
| `FAIL ... HTTP 404` | The URL is wrong, or the routine was deleted | Ask the bot to show its "Message me" webhook again |
| `FAIL ... not set` | A variable is empty | Fill it in `.env` |

---

## 8. Step 7: Connect Cursor (only Project Lead needs it)

Project Lead starts **Cursor Cloud Agents** that write the product code.

1. Open the Cursor dashboard and connect your GitHub account.
2. In the dashboard, open the **Cloud Agents** settings and make sure Cloud Agents is **on** (it is on by default).
3. **Keep "Self-hosted machines" and "Enable my machines" OFF.** If they are on, an agent could run on your own computer, where your `.env` with all your keys lives.
4. Test it: ask Project Lead *"Start a Cursor cloud agent on <a test repo> to add a /health page that returns ok, and send me the PR link."* After a few minutes you get a pull request link.

**Check:** a card with the agent's name and a "View PR" button appears in Project Lead's chat, and a PR exists on GitHub.

---

## 9. Step 8: The full health check

This checks everything at once: Swarms, GitHub, Vercel and the three webhooks.

1. In your home base, open an issue called **Health check** and comment `/ping`.
2. After about 30 seconds the orchestrator replies with a table. You want every row to be ✅ and the last line to say **Setup complete ✅**.
3. Any ❌ row names the step to fix.

---

## 10. Your first project: what to say and what you will see

Talk normally. Project Lead turns it into commands. Here is the whole journey:

| # | You say | What happens by itself | What you answer |
|---|---|---|---|
| 1 | "I have an idea: a habit tracker for students." | Idea Lab (4 agents in parallel) scores it | You read the score |
| 2 | "Build it. Call the repo habit-tracker, public." | A new repo, a Vercel project, secrets and the agent workflow are created in about 30 seconds | Nothing |
| 3 | (wait about 2 minutes) | Deep Dive writes the PRD | "Go", or what to change |
| 4 | | Design phase: a group chat of 4 agents debates the stack | "Go" |
| 5 | | Plan phase: the design is split into 3 to 6 small tasks | "Go" |
| 6 | | Project Lead starts a Cursor Cloud Agent for task 1 | Nothing |
| 7 | | Cursor opens a pull request; the preview is built | Nothing |
| 8 | | A code review runs; QA Tester tests the preview and comments `QA RESULT: PASS`; the release vote runs; Progress Reporter sends screenshots | Nothing |
| 9 | | Project Lead asks: "Release it?" | **"Go"** |
| 10 | | The PR is merged, the CHANGELOG is updated, and the next task starts | Repeat 7 to 10 until all tasks are merged |
| 11 | Later: "Add a daily quiz to the app." | Feature fast path: story, "Go", plan, "Go", then the loop above | "Go" twice, then each release |

**You are always in control:** nothing is created, merged or released without your explicit "Go" in the chat.

---

## 11. Which message goes to which bot

| Event (sent by the orchestrator) | Goes to | The bot does |
|---|---|---|
| `approval_needed` | Project Lead | Summarizes the PRD, design or plan and asks you |
| `repo_created` | Project Lead | Tells you the project is ready |
| `build_task` | Project Lead | Starts a Cursor Cloud Agent with the exact prompt |
| `pr_opened` | Project Lead | Tells you Cursor's PR is ready |
| `changes_requested` | Project Lead | Sends the review fixes to the same Cursor agent |
| `vote_result` | Project Lead | Shows the vote and asks "Release it?" |
| `merged`, `build_done`, `build_failed` | Project Lead | Tells you the result |
| `preview_ready` | Progress Reporter | Screenshots of the preview (desktop and phone) |
| `production_live` | Progress Reporter | Screenshots of the live app |
| `qa_request` | QA Tester | Tests the preview and comments `QA RESULT` on the PR |
| `ping` | any | Says "Webhook works" |

---

## 12. When something goes wrong

| Problem | Likely cause | Fix |
|---|---|---|
| A bot does nothing when it should | Its routine "Message me" is missing, or its instructions are empty | Redo Step 2 and Step 4 for that bot |
| `/ping` shows a ❌ on a webhook row | Wrong URL or key in the **GitHub secrets** (the local test can be fine) | Re-enter that secret in the home base settings |
| Project Lead says it cannot open GitHub | It is not signed in | Do Step 3 |
| The Cursor agent never opens a PR | Still running (big tasks take 20 to 30 minutes), or it stopped | Open its card ("Open in Cursor") and look. If it stopped, comment `/next again` on the project issue |
| QA Tester cannot open the preview | Vercel "Require Log In" is on | `/build` turns it off for new projects. For an old project: Vercel project, Settings, Deployment Protection, off |
| QA Tester says a PR "can't be browser-tested" | The PR only changes SQL, docs or config | Normal. The system skips QA for PRs with no UI |
| The vote says HOLD | A voter found a real blocker (failed QA, a confirmed review problem) | Read the table on the PR, fix, then comment `/vote again` |
| You pasted a secret in chat by mistake | | Rotate that key right away (create a new one and delete the old one) |

---

## 13. Safety rules (read these once)

1. **Bots act as you.** Their GitHub comments appear under your name. Only your own comments can run commands: the orchestrator ignores everyone else.
2. **No secrets in chat, comments, issues or screenshots.** Keys live in `.env` (ignored by git) and in GitHub Actions secrets.
3. **Cursor self-hosted machines stay off** (Step 7).
4. **Nothing ships without your Go.** Creating a repo, merging and releasing all need your explicit yes.
5. **Rotate every key after the hackathon** (Swarms, GitHub, Vercel, and the three webhook keys).

---

## 14. Honest notes (for judges and teammates)

- The **orchestrator** (the Python code in `orchestrator/`) was written with **Claude Code**. The **product code** of every project (for example the English app) is written by **Cursor Cloud Agents**, started by Project Lead.
- The **Swarms API** runs the planning and review agents with different swarm types: `ConcurrentWorkflow` (Idea Lab, Code Review), `HierarchicalSwarm` (Deep Dive), `GroupChat` (Design), `SequentialWorkflow` (Plan, Release, Feature story, Review Verifier), and `MajorityVoting` (Release Vote).
- The share links only copy the bots. They do not copy anything secret, and they do not connect you to anyone else's repo or webhooks.
