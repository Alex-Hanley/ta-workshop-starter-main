import pytest

from app import app, tasks


@pytest.fixture
def client():
    """Provide a Flask test client."""
    app.config['TESTING'] = True
    with app.test_client() as client:
        yield client


@pytest.fixture(autouse=True)
def reset_tasks():
    """Reset the in-memory task list before each test."""
    tasks.clear()
    tasks.extend([
        {"id": 1, "title": "Project-1 Report"},
        {"id": 2, "title": "Project-2 MMFs"}
    ])


def test_index(client):
    """Render the task tracker page with all priority options."""
    response = client.get('/')

    assert response.status_code == 200
    assert b"Task Tracker" in response.data
    assert b'id="task-priority"' in response.data
    assert b'<option value="Low">Low</option>' in response.data
    assert b'<option value="Medium" selected>Medium</option>' in response.data
    assert b'<option value="High">High</option>' in response.data


def test_get_tasks(client):
    """Return all tasks with a default priority for legacy records."""
    response = client.get('/api/tasks')

    assert response.status_code == 200
    data = response.get_json()
    assert len(data) == 2
    assert all(task['priority'] == 'Medium' for task in data)


@pytest.mark.parametrize('priority', ['Low', 'Medium', 'High'])
def test_add_task_accepts_valid_priorities(client, priority):
    """Create a task for each supported priority value."""
    response = client.post(
        '/api/tasks',
        json={"title": f"{priority} task", "priority": priority}
    )

    assert response.status_code == 201
    created_task = response.get_json()
    assert created_task['priority'] == priority

    listed_tasks = client.get('/api/tasks').get_json()
    matching_tasks = [
        task for task in listed_tasks if task['title'] == f"{priority} task"
    ]
    assert matching_tasks[0]['priority'] == priority


def test_add_task_defaults_to_medium_priority(client):
    """Default a task priority to Medium when it is omitted."""
    response = client.post('/api/tasks', json={"title": "Default task"})

    assert response.status_code == 201
    assert response.get_json()['priority'] == 'Medium'

    listed_tasks = client.get('/api/tasks').get_json()
    created_task = [
        task for task in listed_tasks if task['title'] == 'Default task'
    ][0]
    assert created_task['priority'] == 'Medium'


def test_add_task_rejects_invalid_priority(client):
    """Reject a task with a priority outside the supported values."""
    response = client.post(
        '/api/tasks',
        json={"title": "Invalid task", "priority": "Urgent"}
    )

    assert response.status_code == 400
    assert response.get_json()['error'] == 'Invalid priority'
    assert all(task['title'] != 'Invalid task' for task in tasks)


def test_add_task_success(client):
    """Create a task and preserve it in the task list."""
    response = client.post('/api/tasks', json={"title": "Test new task"})

    assert response.status_code == 201
    assert response.get_json()['title'] == "Test new task"
    get_response = client.get('/api/tasks')
    assert len(get_response.get_json()) == 3


def test_add_task_missing_title(client):
    """Reject task creation requests without a title."""
    response = client.post('/api/tasks', json={"wrong_key": "value"})

    assert response.status_code == 400
    assert "error" in response.get_json()

    response2 = client.post('/api/tasks', json={})
    assert response2.status_code == 400


def test_delete_task(client):
    """Delete an existing task."""
    response = client.delete('/api/tasks/1')

    assert response.status_code == 200
    get_response = client.get('/api/tasks')
    data = get_response.get_json()
    assert len(data) == 1
    assert data[0]['id'] == 2
