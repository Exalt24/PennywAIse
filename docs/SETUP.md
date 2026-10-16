# Setup and user guide

## Prerequisites

Python 3.8 or newer (Django 5.2; run here on Python 3.13), Node.js 18 or newer and npm, and internet access in the browser, because Chart.js and marked load from the jsDelivr CDN.

## Steps

```bash
git clone https://github.com/Exalt24/PennywAIse.git
cd PennywAIse
```

Create a `.env` in the project root. Only `SECRET_KEY` and `DEBUG` are needed to start the app:

```dotenv
SECRET_KEY=<your-secret-key>
DEBUG=True                # must be True for local use; with False only the old Render host is allowed

# AI assistant: use one of these two
GENAI_API_KEY=<your-gemini-api-key>
# LLM_BASE_URL=http://localhost:11434/v1
# LLM_MODEL=qwen3:8b
# LLM_REASONING_EFFORT=none   # optional: skips the thinking step of local reasoning models such as qwen3

# Optional: send verification and reset emails through Gmail
# GMAIL_ADDRESS=<your-gmail>@gmail.com
# GMAIL_APP_PASS=<your-16-char-app-password>
```

Generate a key with `python -c "import secrets; print('SECRET_KEY=' + secrets.token_urlsafe(50))"`.

Without the Gmail values, the verification and reset emails are printed to the terminal running the server, so you can still register by opening the link from there. Without an AI setting, the assistant replies that it is not configured.

```bash
npm install
pip install -r requirements.txt     # a virtual environment is a good idea
python manage.py migrate
python manage.py create_test_accounts   # user "testuser", log in with test@example.com / password123
npm run dev
```

The app is at http://127.0.0.1:8000/ with Tailwind rebuilding on change. The first run builds the stylesheet, so give it a few seconds. For another port, run `python manage.py runserver 4950` and `npm run watch:css` (or `npm run build:css` once) in two terminals.

## Authentication details

Registration sends an emailed verification link and the account stays inactive until it is used. A daily job removes accounts left unverified for 48 hours while the dev server is running. Login is by email, and a password reset link is valid for 24 hours. Passwords use Django's default hashing. The dashboard, the entry and report filter endpoints and the AI endpoint require a signed-in user, and every query is filtered to that user's own records.

## AI assistant

Gemini is the default when `GENAI_API_KEY` is set. `LLM_BASE_URL` and `LLM_MODEL` point it at any OpenAI-compatible server instead (the recording used a local Ollama with qwen3:8b). It only sends your question to the model: it does not read your transactions or budgets. The Gemini path was not exercised for the recording, and the default Gemini model id in `budget/views.py` is an old experimental preview, so set `LLM_MODEL` to a current model if you use Gemini.

## User guide

1. Log in with the test account, or register and open the verification link.
2. Dashboard: this month's totals, the six-month trend, the category pie and the budget chart.
3. Add Entry in the sidebar opens a form for title, amount, date, type, category and a note of up to 80 characters.
4. Budgets: pick Total Budget or a category, enter an amount and save. Spent and remaining show in red when over; there are no alerts.
5. Reports: filter by date, type and category, then Export CSV.
6. AI Assistant: type a general budgeting question and press Get Answer.
