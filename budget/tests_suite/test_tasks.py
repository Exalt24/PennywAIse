# budget/tests_suite/test_tasks.py

from django.test import TestCase
from unittest.mock import patch

from budget.tasks import purge_unactivated_users, User


class TasksTestCase(TestCase):
    def test_purge_unactivated_users_no_users(self):
        """
        If there are no unactivated users, we should get a message
        saying "Purged 0 unactivated users".
        """
        result = purge_unactivated_users()
        self.assertIn("Purged 0 unactivated users", result)

    @patch('budget.tasks.User.objects.filter', side_effect=Exception('simulated DB failure'))
    def test_purge_unactivated_users_error(self, mock_filter):
        """
        Simulate an ORM error so that purge_unactivated_users()
        hits its except‐block and returns an error message.
        """
        result = purge_unactivated_users()
       