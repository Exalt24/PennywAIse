# Budget App

A simple Django-based budgeting application with Tailwind CSS styling.

## Prerequisites

* Python 3.x with Django installed
* Node.js and npm

## Setup Instructions

1. Clone the repository:
   ```bash
   git clone <repository-url>
   cd <project-directory>
   ```

2. Install Node.js dependencies:
   ```bash
   npm install
   ```

3. Install additional Python packages:
   ```bash
   pip install django-browser-reload
   pip install django-debug-toolbar
   ```

4. Apply database migrations:
   ```bash
   python manage.py migrate
   ```

## Running the Development Server

Start both the Django development server and Tailwind CSS compiler with a single command:

```bash
npm run dev
```

This will:
- Launch the Django development server at http://127.0.0.1:8000/
- Start the Tailwind CSS watcher to recompile CSS when changes are made
- Configure browser auto-reloading when templates are modified