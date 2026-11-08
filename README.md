# Agentic Build Workflow

Talk to a Grok Bot about an idea. A team of AI agents on the Swarms API plans it, Cursor writes the code, Grok Bot tests it like a real user, and nothing ships until you approve it.

## Start here: set up the three bots

**[docs/HOWTO-GROK-BOTS.md](docs/HOWTO-GROK-BOTS.md)** is the step-by-step guide for the hackathon: add the three Grok Bot agents with one click each, give them their instructions, connect their webhooks, test each connection with one command, and run your first project.

| Bot | Add it to your Grok Bot |
|---|---|
| Project Lead (you talk to this one) | https://x.ai/bot/egDXuf_4KO1c8LnAUNbbl |
| Progress Reporter (screenshots) | https://x.ai/bot/tXR4LtstF90Dkx33p0yqA |
| QA Tester (tests each preview) | https://x.ai/bot/NEcmLsDFXM35i7mVwiOEZ |

Then follow [docs/SETUP.md](docs/SETUP.md) for tokens and secrets.

---

- `PLAN.md` has the full design, the setup tests and the build timeline.
- `CONTEXT.md` has the latest decisions, what is done and what is next.
- Copy `.env.example` to `.env` and fill in your own values. `.env` is ignored by git, so never commit it.

---

## Running this on your own machine

Cursor's Cloud Agents page has two settings that let agents run on your own computer instead of Cursor's cloud:

- **Self-hosted machines**
- **Enable my machines**

Keep both **off** for this project.

If you turn them on, agents started from the web, mobile, Slack or the API can run on your machine. Your machine holds your `.env`, which has your Swarms key, GitHub token and webhook keys. Agents in Cursor's cloud only work with the repo they were started on.

If you set this up locally anyway, keep `.env` out of any folder an agent worker runs in, and rotate your keys afterwards.
