# External Appointment Scheduler - Testing Guide

## Running Tests

### Run All Tests

```bash
# From Odoo root directory
python odoo-bin -c conf/odoo.conf -d your_database --test-enable --stop-after-init -i external_appointment_scheduler
```

### Run Specific Test Module

```bash
# Test appointments only
python odoo-bin -c conf/odoo.conf -d test_db --test-enable --stop-after-init --test-tags external_appointment
```

### Run Specific Test Class

```bash
# Test specific class
python odoo-bin -c conf/odoo.conf -d test_db --test-enable --stop-after-init --test-tags external_appointment_scheduler.tests.test_external_appointment.TestExternalAppointment
```

### Test Coverage

```bash
# Install coverage
pip install coverage

# Run with coverage
coverage run --source=custom_modules/external_appointment_scheduler odoo-bin -c conf/odoo.conf -d test_db --test-enable --stop-after-init -i external_appointment_scheduler

# Generate report
coverage report
coverage html
```

## Test Structure

### Unit Tests

1. **test_external_appointment.py** (17 tests)
   - Basic CRUD operations
   - Constraint validations
   - Status workflow
   - Computed fields
   - Business logic

2. **test_calendar_config.py** (9 tests)
   - Calendar configuration
   - Service management
   - Provider constraints
   - Connection status

3. **test_adapters.py** (7 tests)
   - Adapter initialization
   - Google Calendar adapter
   - Abstract base adapter
   - Factory pattern

### Integration Tests

4. **test_integration.py** (15 tests)
   - Complete booking flow
   - API endpoints
   - Portal pages
   - Webhook handling
   - Email notifications
   - Cron jobs

## Test Database Setup

### Create Test Database

```bash
# Create fresh test database
python odoo-bin -c conf/odoo.conf -d test_appointment_db --stop-after-init -i base
```

### Reset Test Database

```bash
# Drop and recreate
dropdb test_appointment_db
createdb test_appointment_db
python odoo-bin -c conf/odoo.conf -d test_appointment_db --stop-after-init -i external_appointment_scheduler --test-enable
```

## Test Categories

Tests are tagged for selective execution:

- `post_install` - Run after module installation
- `-at_install` - Don't run during installation
- `external_appointment` - All appointment scheduler tests

## Continuous Integration

### GitHub Actions Example

```yaml
name: Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    services:
      postgres:
        image: postgres:15
        env:
          POSTGRES_DB: test_db
          POSTGRES_USER: odoo
          POSTGRES_PASSWORD: odoo
        ports:
          - 5432:5432

    steps:
      - uses: actions/checkout@v3
      
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.10'
      
      - name: Install dependencies
        run: |
          pip install -r requirements.txt
          pip install coverage
      
      - name: Run tests
        run: |
          coverage run odoo-bin -c conf/odoo.conf -d test_db --test-enable --stop-after-init -i external_appointment_scheduler
      
      - name: Generate coverage report
        run: coverage xml
      
      - name: Upload coverage
        uses: codecov/codecov-action@v3
```

## Mock Testing

For tests requiring external API calls (Google Calendar), use mocking:

```python
from unittest.mock import patch, MagicMock

@patch('google.oauth2.credentials.Credentials')
def test_with_mocked_google(self, mock_creds):
    mock_creds.return_value = MagicMock()
    # Test code here
```

## Test Data

Demo data is available for testing:
- 3 demo services (Consultation, Follow-up, Workshop)
- Located in `demo/appointment_services_demo.xml`

## Known Issues

1. **Google API Tests**: Tests requiring real Google API credentials will fail in test environment. Use mocking or skip with `@unittest.skipIf`.

2. **Webhook Tests**: Require HTTPS endpoints. Skip in local dev or use ngrok for testing.

3. **Email Tests**: Use Odoo's `mock_mail_gateway()` context manager.

## Test Checklist

Before release, verify:

- [ ] All unit tests pass
- [ ] All integration tests pass
- [ ] Coverage > 80%
- [ ] No test database pollution
- [ ] Proper test isolation
- [ ] Mocked external dependencies
- [ ] Portal tests with authenticated user
- [ ] API endpoint tests
- [ ] Webhook signature validation
- [ ] Email template rendering
- [ ] Cron job execution

## Performance Testing

For load testing the booking API:

```bash
# Install locust
pip install locust

# Create locustfile.py with booking scenarios
# Run load test
locust -f tests/load_test.py --host=http://localhost:8069
```

## Debugging Tests

```bash
# Run with debugger
python -m pdb odoo-bin -c conf/odoo.conf -d test_db --test-enable --stop-after-init -i external_appointment_scheduler

# Verbose output
python odoo-bin -c conf/odoo.conf -d test_db --test-enable --stop-after-init -i external_appointment_scheduler --log-level=test
```

---

**Total Test Count:** 48 tests
**Estimated Run Time:** 30-60 seconds
**Last Updated:** December 6, 2025
