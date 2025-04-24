import json
import unittest
import gzip
from nose.tools import assert_equal, assert_in, assert_true
from examples.flask.hello import app

class TestHelloApp(unittest.TestCase):

  def setUp(self):
    """Set up test client before each test."""
    self.app = app.test_client()
    self.app.testing = True

  def test_index_route(self):
    """Test the index route."""
    response = self.app.get('/')
    assert_equal(response.status_code, 200)
    assert_equal(response.data.decode('utf-8'), 'Index Page')

  def test_hello_route(self):
    """Test the hello route."""
    response = self.app.get('/hello')
    assert_equal(response.status_code, 200)
    assert_equal(response.data.decode('utf-8'), 'Hello, world')

  def test_user_profile_route(self):
    """Test the user profile route."""
    response = self.app.get('/user/testuser')
    assert_equal(response.status_code, 200)
    assert_equal(response.data.decode('utf-8'), 'User testuser')

  def test_show_post_route(self):
    """Test the show post route."""
    response = self.app.get('/post/123')
    assert_equal(response.status_code, 200)
    assert_equal(response.data.decode('utf-8'), 'Post 123')

  def test_error_route(self):
    """Test the error route."""
    # We expect a ValueError to be raised
    with self.assertRaises(ValueError):
      self.app.get('/error')

  def test_get_tasks_route(self):
    """Test getting all tasks."""
    response = self.app.get('/todo/api/v1.0/tasks')
    assert_equal(response.status_code, 201)
    assert_equal(response.content_type, 'application/json')
    data = json.loads(response.data)
    assert_in('tasks', data)
    assert_equal(len(data['tasks']), 2)

  def test_get_specific_task_route(self):
    """Test getting a specific task."""
    # Test existing task
    response = self.app.get('/todo/api/v1.0/tasks/1')
    assert_equal(response.status_code, 201)
    data = json.loads(response.data)
    assert_in('task', data)
    assert_equal(data['task']['id'], 1)

    # Test non-existent task
    response = self.app.get('/todo/api/v1.0/tasks/999')
    assert_equal(response.status_code, 404)

  def test_create_task_route(self):
    """Test creating a new task."""
    # Valid request
    response = self.app.post(
      '/todo/api/v1.0/tasks',
      data=json.dumps({'title': 'Test Task', 'description': 'Test Description'}),
      content_type='application/json'
    )
    assert_equal(response.status_code, 201)
    data = json.loads(response.data)
    assert_equal(data['task']['title'], 'Test Task')

    # Invalid request (missing title)
    response = self.app.post(
      '/todo/api/v1.0/tasks',
      data=json.dumps({'description': 'No Title Here'}),
      content_type='application/json'
    )
    assert_equal(response.status_code, 400)

  def test_update_users_route(self):
    """Test updating a user."""
    user_id = 'test_user_123'
    response = self.app.post(f'/users/{user_id}')
    assert_equal(response.status_code, 201)
    data = json.loads(response.data)
    assert_equal(data['user_id'], user_id)
    assert_equal(data['update_users'], 'success')

  def test_update_companies_route(self):
    """Test updating a company."""
    company_id = 'test_company_456'
    response = self.app.post(f'/companies/{company_id}')
    assert_equal(response.status_code, 201)
    data = json.loads(response.data)
    assert_equal(data['company_id'], company_id)
    assert_equal(data['update_companies'], 'success')

  def test_html_response_route(self):
    """Test HTML response."""
    response = self.app.get('/test/html_response')
    assert_equal(response.status_code, 200)
    assert_equal(response.content_type, 'text/html')
    assert_in(b'<h1>My First Heading</h1>', response.data)

  def test_xml_response_route(self):
    """Test XML response."""
    response = self.app.get('/test/xml_response')
    assert_equal(response.status_code, 200)
    assert_equal(response.content_type, 'application/xml')
    assert_in(b'<note>', response.data)

  def test_json_response_route(self):
    """Test JSON response."""
    response = self.app.get('/test/json_response')
    assert_equal(response.status_code, 201)
    assert_equal(response.content_type, 'application/json')
    data = json.loads(response.data)
    assert_in('response', data)
    assert_equal(len(data['response']), 2)

  def test_gzip_response_route(self):
    """Test gzipped response."""
    response = self.app.post('/test/gzip_response')
    assert_equal(response.status_code, 201)
    assert_equal(response.headers.get('Content-Encoding'), 'gzip')

    # Decompress and verify content
    decompressed = gzip.decompress(response.data)
    data = json.loads(decompressed)
    assert_equal(len(data), 2)
    assert_equal(data[0], {'a': 1, 'b': 2})
    assert_equal(data[1], {'c': 3, 'd': 4})

  def test_not_found_handler(self):
    """Test 404 error handler."""
    response = self.app.get('/nonexistent/path')
    assert_equal(response.status_code, 404)
    data = json.loads(response.data)
    assert_equal(data['error'], 'Not found')

if __name__ == '__main__':
  unittest.main()
