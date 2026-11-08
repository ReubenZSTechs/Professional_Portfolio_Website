# Security policy

Thank you for taking the time to look. This is a personal portfolio, but it runs a
public chatbot API and a contact form, so I take reports seriously.

## Scope

In scope:

- **The live site**: the production deployment of this portfolio on Vercel, including its
  pages, the contact form and the chatbot UI.
- **The `/api/py` endpoints**: the Python (FastAPI) backend behind the chatbot and contact
  form, for example prompt-injection that leaks secrets or system prompts, bypassing rate
  limits, reaching data in Supabase you should not, or abusing the contact form to send
  mail to arbitrary recipients.
- **This repository**: source code, GitHub Actions workflows and committed configuration,
  for example a leaked secret, an injectable workflow or a vulnerable pinned dependency
  that is actually reachable.

Out of scope:

- Volumetric or resource-exhaustion denial of service (floods, load testing, mass bot traffic).
- Social engineering, phishing or physical attacks against me or anyone else.
- Findings that need a compromised device, browser, or account to work (malware, a
  rooted phone, a stolen session).
- Reports from automated scanners with no demonstrated impact, missing best-practice
  headers with no exploit, and self-XSS.
- Vulnerabilities in third-party services themselves (Vercel, Supabase, Google Gemini,
  Resend). Please report those to the vendor.
- The chatbot giving a wrong or odd answer. That is a quality issue, not a vulnerability,
  unless it exposes data or secrets.

## Reporting a vulnerability

Please report privately. **Do not open a public issue or pull request.**

- **GitHub private vulnerability reporting** (preferred): on this repository's
  **Security** tab, choose **Report a vulnerability**.
- **Email**: [reuben.zachary.rz@gmail.com](mailto:reuben.zachary.rz@gmail.com) with
  "Security" in the subject.

Helpful details: what you found, the URL or file involved, steps to reproduce, and the
impact you think it has. Please do not access, change or delete data that is not yours,
and stop once you have shown the issue.

## What to expect

- **Acknowledgement within 5 working days** of your report.
- A follow-up with my assessment and, if it is valid, a planned fix and rough timeline.
- A note when the fix is live. I am happy to credit you in the fix commit or release
  notes if you would like.

This is a personal project, so there is no bug bounty. Good-faith research that follows
this policy will not be met with legal action.
