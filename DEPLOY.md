# Deploying PUF-Pay to Streamlit Community Cloud (free, public HTTPS)

This gives you a public `https://…streamlit.app` URL for the hackathon submission.
No servers, no cost, no AWS. Deploys straight from your GitHub repo.

---

## One-time: what's already set up for you

- `requirements.txt` — only `streamlit`, `ecdsa`, `faker` (no AWS/boto3 anymore).
- `app.py` — runs the full pipeline **on-device**, no cloud calls, can't fail on a network.
- `.streamlit/config.toml` — dark theme so it looks right on the cloud.
- All data + PUF key files are committed, so the cloud copy has everything it needs.

You do **not** need an API key. The app works fully offline. (See the optional step at the end.)

---

## Steps (about 3 minutes)

1. Go to **https://share.streamlit.io** and click **Sign in with GitHub**.
   Approve the GitHub access it asks for (this is the one login only you can do).

2. Click **Create app** → **Deploy a public app from GitHub**.

3. Fill the form:
   - **Repository:** `jayjain2365/ChipVault`
   - **Branch:** `main`
   - **Main file path:** `app.py`
   - (Optional) **App URL:** pick something like `puf-pay`

4. Click **Advanced settings** → set **Python version** to **3.12** (or 3.13). Leave everything else.

5. Click **Deploy**. First build takes ~2–4 minutes while it installs the packages.
   When it finishes you'll have a live URL like `https://puf-pay.streamlit.app` — that's your submission link.

That's it. Any time you push new code to `main`, Streamlit Cloud auto-redeploys.

---

## Optional: make the compliance memo a *live* AI (still free)

By default the compliance memo is written by an on-device template — genuine, formal,
and it never needs the internet. If you'd like it written by a real LLM (so you can tell
the jury "the memo is live-generated"):

1. Get a **free** Groq API key at **https://console.groq.com** (no credit card).
2. In your deployed app: **Manage app** (bottom-right) → **Settings** → **Secrets**.
3. Paste this and save:

   ```toml
   GROQ_API_KEY = "gsk_your_key_here"
   ```

4. The app restarts and the header badge changes to **"Groq Llama-3.1 (live)"** automatically.
   If Groq is ever unreachable, it silently falls back to the on-device memo — the demo
   never breaks.

(You can use `ANTHROPIC_API_KEY` instead if you prefer Claude — same steps.)

---

## Troubleshooting

- **App is "sleeping":** free apps sleep after inactivity. Just open the URL and it wakes in ~30s.
  Open it a few minutes before your demo so it's warm.
- **Build failed on a package:** confirm the Python version is 3.12/3.13 in Advanced settings.
- **Want to run it locally too:** `streamlit run app.py`, then open `http://127.0.0.1:8501`.
