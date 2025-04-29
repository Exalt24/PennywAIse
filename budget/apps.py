from django.apps import AppConfig
import sys

class BudgetConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'budget'

    def ready(self):
        import budget.signals
        if 'runserver' not in sys.argv:
            return

        # delay imports until here
        from apscheduler.schedulers.background import BackgroundScheduler
        from django_apscheduler.jobstores import DjangoJobStore

        # avoid double-starting on auto-reload
        if hasattr(self, 'apscheduler'):
            return

        scheduler = BackgroundScheduler()
        scheduler.add_jobstore(DjangoJobStore(), "default")

        # schedule via textual reference
        scheduler.add_job(
            func='budget.tasks:purge_unactivated_users',
            trigger='cron',
            hour=3,
            minute=0,
            id='purge_unactivated_users',
            replace_existing=True,
        )

        scheduler.start()
        self.apscheduler = scheduler