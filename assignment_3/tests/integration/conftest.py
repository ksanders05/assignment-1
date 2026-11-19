"""Fixtures for your integration tests (Section 4 of the assignment).

Your integration tests assemble the REAL repository and service on a
REAL SQLite database file -- inside the test process. Suggested fixtures
(write them here):

  - a connection to a new database file in pytest's `tmp_path`, with
    db.create_schema() applied and a few students and courses added
    through the repository (or with db.seed());
  - a RegistrationRepository on that connection;
  - a fake notifier: a small class of your own that records every
    send_confirmation / send_rejection call in a list, so a test can
    check what was sent;
  - a RegistrationService built from the three.
"""

import pytest
import sqlite3
from src.db import connect, create_schema
from src.repository import RegistrationRepository
from src.service import RegistrationService

class FakeNotifier:
    """A fake notifier for integration testing that records every call in a list[cite: 4]."""
    def __init__(self):
        self.outbox = []

    def send_confirmation(self, student_id, course_code, fee):
        self.outbox.append(("confirmation", student_id, course_code, fee))

    def send_rejection(self, student_id, course_code, reason):
        self.outbox.append(("rejection", student_id, course_code, reason))

@pytest.fixture
def db_conn(tmp_path):
    """Provides a fresh SQLite database for each test using tmp_path[cite: 4]."""
    db_file = tmp_path / "test.db"
    conn = connect(str(db_file))
    create_schema(conn)
    yield conn
    conn.close()

@pytest.fixture
def sample_data(db_conn):
    """Seeds a small set of students and courses[cite: 4]."""
    cursor = db_conn.cursor()
    cursor.execute("INSERT INTO students (id, name) VALUES ('S01', 'Alice')")
    cursor.execute("INSERT INTO students (id, name) VALUES ('S02', 'Bob')")
    cursor.execute("INSERT INTO courses (code, title, credits, capacity, seats_taken, prerequisite) VALUES ('CIS350', 'Software Engineering', 4, 40, 0, NULL)")
    cursor.execute("INSERT INTO courses (code, title, credits, capacity, seats_taken, prerequisite) VALUES ('SE499', 'Capstone', 3, 2, 0, 'CIS350')")
    cursor.execute("INSERT INTO completed (student_id, course_code) VALUES ('S01', 'CIS350')")
    cursor.execute("INSERT INTO completed (student_id, course_code) VALUES ('S02', 'CIS350')")
    db_conn.commit()

@pytest.fixture
def repo(db_conn):
    return RegistrationRepository(db_conn)

@pytest.fixture
def fake_notifier():
    return FakeNotifier()

@pytest.fixture
def service(db_conn, repo, fake_notifier):
    return RegistrationService(db_conn, repo, fake_notifier)