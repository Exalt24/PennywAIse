# PennywAIse

PennywAIse is a Django‑powered budgeting dashboard designed to help you take control of your finances. With a clean Tailwind CSS design, interactive Chart.js visualizations, and an intuitive interface—plus our AI‑driven insight engine—PennywAIse makes tracking income, expenses, and budgets both simple and transformative.

---

## ✨ Key Features

1. **AI‑Powered Financial Coaching**

   - Get intelligent, personalized tips on where to save, which subscriptions to trim, and how to optimize your spending habits—instantly, based on your real data.

2. **Secure User Authentication**

   - **Registration & Login**: Sign up, log in, and out securely; passwords are hashed and safely stored.
   - **Access Control**: All dashboard views are protected—only authenticated users can access or modify data.

3. **Income & Expense Management**

   - **Add / Edit / Delete Entries**: Record a title, amount, date, type (Income/Expense), category, and optional notes.
   - **Categorization**: Organize your transactions into custom or preset categories (Food, Travel, Bills, etc.).

4. **Visual Dashboard**

   - **Net Balance Card**: See total income, total expenses, and remaining balance for the current month.
   - **Charts & Graphs**: Pie chart of expense breakdown by category; bar/line charts showing trends over time.
   - **Quick Stats**: Transaction counts, month‑to‑month comparisons, and real‑time filtering.

5. **Budgets & Alerts** *(Stretch Goal)*

   - Define monthly budgets (overall or per category) and receive over‑budget warnings.

6. **Data Export** *(Stretch Goal)*

   - Export your entries or reports as CSV for deeper analysis in Excel or Google Sheets.

---

## 🚀 Prerequisites

- **Python 3.8+** and **Node.js 14+**
- **pip**, **npm**, and **Git** installed

---

## 🛠️ Setup & Development

1. **Clone the repository**

   ```bash
   git clone https://github.com/Exalt24/WebEngLongExam2.git
   cd WebEngLongExam2
   ```

2. **Environment variables**
   Create a `.env` file in the project root:
   ```dotenv
   SECRET_KEY=<your-secret-key>
   DEBUG=True                # False in production
   GMAIL_ADDRESS=<your-gmail>@gmail.com
   GMAIL_APP_PASS=<your-16-char-app-password>
   GENAI_API_KEY=<your-gemini-api-key>
   ```
   #### Generate Your Secret Key
   Run this command in your terminal to generate a secure random key:
   ```bash
   python -c "import secrets; print('SECRET_KEY=' + secrets.token_urlsafe(50))"
   ```

   Copy the output (everything after `SECRET_KEY=`) and paste it as the value for `SECRET_KEY` in your `.env` file.

   #### Complete Your Configuration
   - Replace `youremail@gmail.com` with your actual Gmail address
   - For `GMAIL_APP_PASS`, create an app password in your Google Account settings
   - Get a Gemini API key from Google AI Studio for the `GENAI_API_KEY`

3. **Install dependencies**

   ```bash
   npm install             # Tailwind & tooling
   pip install -r requirements.txt
   ```

4. **Apply database migrations**

   ```bash
   python manage.py makemigrations
   python manage.py migrate
   ```

5. **Create a test user**

   ```bash
   # Built‑in helper to create a user for development/testing (email: test@example.com, password: password123)
   python manage.py create_test_user
   ```

6. **Run in development mode**

   ```bash
   npm run dev
   ```

   - Django server at `http://127.0.0.1:8000/`
   - Tailwind CSS watcher & auto‑reload enabled

---

## ✅ Testing Suite

All tests live under the `budget` app. You can run:

- **All tests**:

  ```bash
  python manage.py test budget
  ```

- **Specific module**:

  ```bash
  python manage.py test budget.test_models
  python manage.py test budget.test_forms
  python manage.py test budget.test_views
  python manage.py test budget.test_security
  python manage.py test budget.test_integration
  ```

- **Specific class or method**:

  ```bash
  python manage.py test budget.test_models.CategoryModelTest
  python manage.py test budget.test_models.CategoryModelTest.test_category_creation
  ```

### Coverage Report

```bash
pip install coverage
python -m coverage run --source='budget' manage.py test budget
python -m coverage report
python -m coverage html   # view `htmlcov/index.html`
```

---

## 👥 Team & Division of Labor

| Member                 | Responsibility                                                                              |
|------------------------|---------------------------------------------------------------------------------------------|
| Amielle Jaezxier Perez | Testing framework, Models & business logic                                                  |
| Daniel Alexis Cruz     | Authentication, Email workflows, Models & business logic, Tailwind integration, Frontend UI |
| Nikka Joie Mendoza     | Frontend UI & refinement, Tailwind Integration                                              |

---

## 📖 Usage Guide

1. **Log in** or **register** to access your dashboard.
2. **Add** income/expense entries via the form in the sidebar.
3. **Categorize** each entry and watch your Dashboard update in real time.
4. Use the **AI suggestions** card to get personalized recommendations.
5. **Set budgets** and get alerted when you approach limits.
6. **Export** data via the Reports page for further analysis.

Enjoy taking control of your financial future with PennywAIse!

