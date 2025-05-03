from django.test import TestCase
from unittest.mock import patch, MagicMock, Mock
import sys
from budget.apps import BudgetConfig

class AppConfigTests(TestCase):
    def test_ready_with_runserver(self):
        """Test ready method when runserver is in sys.argv"""
        # Add runserver to sys.argv
        original_argv = sys.argv.copy()
        if 'runserver' not in sys.argv:
            sys.argv.append('runserver')
            
        try:
            # Create a mock scheduler and job store
            mock_scheduler = MagicMock()
            mock_jobstore = MagicMock()
            
            # Mock the required imports
            with patch('apscheduler.schedulers.background.BackgroundScheduler', return_value=mock_scheduler), \
                 patch('django_apscheduler.jobstores.DjangoJobStore', return_value=mock_jobstore), \
                 patch('budget.signals'):
                
                # Create a mock of BudgetConfig with the actual ready method
                mock_config = Mock(spec=BudgetConfig)
                mock_config.name = 'budget'
                mock_config.ready = BudgetConfig.ready.__get__(mock_config, BudgetConfig)
                
                # Call the ready method
                mock_config.ready()
                
                # Check that the scheduler was properly configured
                mock_scheduler.add_jobstore.assert_called_once_with(mock_jobstore, "default")
                mock_scheduler.add_job.assert_called_once()
                
                # Check job parameters
                job_args = mock_scheduler.add_job.call_args[1]
                self.assertEqual(job_args['func'], 'budget.tasks:purge_unactivated_users')
                self.assertEqual(job_args['trigger'], 'cron')
                self.assertEqual(job_args['hour'], 3)
                self.assertEqual(job_args['minute'], 0)
                self.assertEqual(job_args['id'], 'purge_unactivated_users')
                self.assertEqual(job_args['replace_existing'], True)
                
                # Verify scheduler started
                mock_scheduler.start.assert_called_once()
                
                # Verify apscheduler attribute was set
                self.assertEqual(mock_config.apscheduler, mock_scheduler)
                
                # Call ready again to test the hasattr branch
                # First, make hasattr return True to simulate having the attribute
                with patch('builtins.hasattr', return_value=True):
                    mock_config.ready()
                
                # Verify scheduler was only started once
                mock_scheduler.start.assert_called_once()
                
        finally:
            # Restore original sys.argv
            sys.argv = original_argv
    
    def test_ready_without_runserver(self):
        """Test ready method without runserver in sys.argv"""
        # Make sure runserver is not in sys.argv
        original_argv = sys.argv.copy()
        sys.argv = [arg for arg in sys.argv if arg != 'runserver']
        
        try:
            # Mock BackgroundScheduler to verify it's not called
            with patch('apscheduler.schedulers.background.BackgroundScheduler') as mock_scheduler_class, \
                 patch('budget.signals'):
                
                # Create a mock of BudgetConfig with the actual ready method
                mock_config = Mock(spec=BudgetConfig)
                mock_config.name = 'budget'
                mock_config.ready = BudgetConfig.ready.__get__(mock_config, BudgetConfig)
                
                # Call the ready method
                mock_config.ready()
                
                # Verify scheduler class was not called
                mock_scheduler_class.assert_not_called()
                
                # Verify apscheduler attribute was not set
                self.assertFalse(hasattr(mock_config, 'apscheduler'))
                
        finally:
            # Restore original sys.argv
            sys.argv = original_argv 