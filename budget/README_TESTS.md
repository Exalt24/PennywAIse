# Budget Tracker Test Suite

This document provides information about the test suite for the Budget Tracker application.

## Test Structure

The test suite is organized into several modules to ensure comprehensive coverage of the application:

1. **Model Tests** (`test_models.py`): Tests for the Category and Entry models.
2. **Form Tests** (`test_forms.py`): Tests for all forms in the application.
3. **View Tests** (`test_views.py`): Tests for all views in the application.
4. **Security Tests** (`test_security.py`): Tests for security features and access control.
5. **Integration Tests** (`test_integration.py`): Tests for the application as a whole, including user journey flows.

All tests are also imported into the main `tests.py` file for consolidated test execution.

## Running Tests

### Running All Tests

To run all tests:

```bash
python manage.py test budget
```

### Running Specific Test Modules

To run specific test modules:

```bash
# Run model tests
python manage.py test budget.test_models

# Run form tests
python manage.py test budget.test_forms

# Run view tests
python manage.py test budget.test_views

# Run security tests
python manage.py test budget.test_security

# Run integration tests
python manage.py test budget.test_integration
```

### Running Specific Test Classes

To run a specific test class:

```bash
python manage.py test budget.test_models.CategoryModelTest
```

### Running a Specific Test Method

To run a specific test method:

```bash
python manage.py test budget.test_models.CategoryModelTest.test_category_creation
```

## Test Coverage

You can generate a test coverage report to see how much of your code is covered by tests. First, install `coverage`:

```bash
pip install coverage
```

Then run:

```bash
# Run tests with coverage
python -m coverage run --source='budget' manage.py test budget

# Generate a report
python -m coverage report

# For a detailed HTML report
python -m coverage html
```

The HTML report will be available in the `htmlcov` directory, and you can open `index.html` in your browser.

## Guidelines for Writing New Tests

When adding new features or modifying existing ones, please follow these guidelines for writing tests:

1. **Keep tests focused**: Each test should test one specific aspect of the code.
2. **Use meaningful names**: Test method names should clearly describe what is being tested.
3. **Follow the AAA pattern**: Arrange, Act, Assert.
4. **Keep tests independent**: Tests should not depend on each other.
5. **Mock external dependencies**: Use mocks or stubs for external services.
6. **Use test fixtures**: Use setUp and tearDown methods for repeated code.
7. **Test edge cases**: Consider boundary conditions and error cases.
8. **Test security implications**: Consider permission checks and data isolation.

## CI/CD Integration

These tests are automatically run as part of our CI/CD pipeline. Any pull request will trigger the test suite, and all tests must pass before merging.

## Troubleshooting

If you're having issues with the tests:

1. Make sure your database settings are correctly configured for testing
2. Check that you have all required dependencies installed
3. Ensure you're running the tests from the project root directory
4. If a test is failing, use the `-v 2` flag for more verbose output:
   ```
   python manage.py test budget -v 2
   ``` 