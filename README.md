# PennywAIse

PennywAIse is a Django-powered budgeting dashboard designed to help you take control of your finances. With a clean Tailwind CSS design, interactive Chart.js visualizations, and an intuitive interface, PennywAIse makes tracking income, expenses, and budgets both simple and insightful.

## ✨ Features

### 1. Secure User Authentication

- **User Registration**: Create an account with your email and a secure password. All passwords are hashed and safely stored.
- **User Login**: Access your personal dashboard with a simple login form. Unauthenticated users are redirected to the login page to protect your data.
- **Access Control**: All dashboard views are protected—only authenticated users can view or modify data.

### 2. Dashboard Overview

- **Net Balance Card**: Instantly see your total income, total expenses, and net balance for the current month.
- **Trend Chart**: View a line chart displaying income and expenses over the last six months, helping you spot patterns and seasonality.
- **Transaction Count**: See the total number of entries made this month at a glance.

### 3. Budgets Management

- **Set Monthly Budgets**: Allocate a budget for the entire month or per category.
- **Donut Charts**: Visualize your overall budget utilization and compare budget vs. actual spending by category.
- **Dynamic Switching**: Toggle between overall budget and per-category breakdown within a single card.

### 4. Categories

- **CRUD Operations**: Add new spending categories (e.g., Groceries, Utilities), edit existing ones, or delete unused categories.
- **Summary Table**: View the number of entries, total income, expenses, and net balance per category.
- **Sortable Columns**: Click on table headers to sort categories by name, entry count, income, expenses, or net balance.

### 5. Income & Expense Entries

- **Entry Form**: Record income or expenses with title, amount, date, type, category, and optional notes.
- **Edit & Delete**: Modify or remove entries directly from the dashboard.
- **Real-Time Filtering**: Filter entries by date range, title keyword, category, and amount range without reloading the page.

### 6. Reports & CSV Export

- **Dynamic Reporting**: Run customized reports by selecting date range, entry type (income/expense), and category.
- **Instant CSV Export**: Download your filtered report as a CSV file ready for analysis in Excel or Google Sheets.
- **Consistent Formatting**: Amounts are exported as raw numbers (no currency symbols), ensuring compatibility with spreadsheet calculations.

## ⚙️ Prerequisites

- **Python 3.8+** with Django installed
- **Node.js 14+** and npm

## 🛠 Setup Instructions

1. **Clone the repository**

   ```bash
   git clone https://github.com/Exalt24/WebEngLongExam2.git
   cd WebEngLongExam2
   ```

2. **Install Node.js dependencies**

   ```bash
   npm install
   ```

3. **Install Python dependencies**

   ```bash
   pip install python-dateutil
   ```

4. **Apply database migrations**

   ```bash
   python manage.py makemigrations
   python manage.py migrate
   ```

## 🏃‍♂️ Running the Development Server

Start the Django development server and Tailwind CSS watcher together:

```bash
npm run dev
```

This command will:

- Launch Django at [http://127.0.0.1:8000/](http://127.0.0.1:8000/)
- Watch and recompile Tailwind CSS automatically
- Enable browser auto-reload on template or static file changes

