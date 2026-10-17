# Shikayat Saathi

A small FastAPI demo for the Sarvam AI hackathon: speak a civic complaint, receive one spoken follow-up if needed, then get English and native-language grievance letters.

## Safe setup

1. Copy `.env.example` to `.env`.
2. Add your Sarvam key after `SARVAM_API_KEY=`. Do not paste it into chat, source code, or commit it.
3. Create and activate a virtual environment, then install the dependencies:

   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt
   ```

4. Run the app:

   ```bash
   uvicorn app.main:app --reload
   ```

5. Open <http://127.0.0.1:8000>. Allow microphone access, hold **Hold to speak**, and speak a short Telugu, Hindi, or English complaint.

## Deploy with GitHub and Vercel

GitHub stores the code; Vercel runs the FastAPI backend. Do not use GitHub Pages for this app because it cannot safely run the Python backend or protect the Sarvam key.

1. Create an empty GitHub repository, then from this folder run:

   ```bash
   git init
   git add .
   git status
   git commit -m "Build Shikayat Saathi MVP"
   git branch -M main
   git remote add origin YOUR_GITHUB_REPOSITORY_URL
   git push -u origin main
   ```

   Confirm `git status` does not list `.env` before committing.

2. In Vercel, choose **Add New → Project**, import that GitHub repository, and deploy it. Vercel detects the FastAPI application through `app/app.py`.

3. Before the first deployment, open **Project Settings → Environment Variables** and add `SARVAM_API_KEY` with your real key. Do not add the key to GitHub or any source file.

## Verified Sarvam integration

- `POST https://api.sarvam.ai/speech-to-text`: multipart `file`, with `model=saaras:v4` and `language_code=unknown`. Browser WebM is supported.
- `POST https://api.sarvam.ai/v1/chat/completions`: `model=sarvam-105b`, `messages`, and JSON response mode for analysis and letter generation.
- `POST https://api.sarvam.ai/text-to-speech`: `model=bulbul:v3`, `text`, BCP-47 `language_code`, and `output_audio_codec=wav`.

All calls use the `api-subscription-key` header only on the server. The frontend never receives the key.

## Quick test sequence

1. Say an incomplete complaint without a location; confirm a single question appears and is spoken.
2. Answer it using **Hold to answer**; confirm no second question is asked.
3. Review both letters, copy them, and use **Read my letter aloud**.

The app does not store audio, accounts, databases, or real-government filing. It is a drafting aid, not legal advice.
