from flask import Flask, jsonify, request
from moesifwsgi import MoesifMiddleware

# Initialize Flask app
app = Flask(__name__)

# Moesif Middleware options
def identify_user(app, environ, response_headers=dict()):
  return environ.get('HTTP_X_USER_ID', '12345')  # Default to '12345' if header is not present

def identify_company(app, environ, response_headers=dict()):
  return environ.get('HTTP_X_COMPANY_ID', '67890')  # Default to '67890' if header is not present

moesif_settings = {
    'APPLICATION_ID': 'eyJhcHAiOiI0OTM6MTg3NSIsInZlciI6IjIuMSIsIm9yZyI6Ijg4OjIxMCIsImlhdCI6MTc0MzQ2NTYwMH0.dzwkeeBSCbrM1wizJC86iT953vEC0ZhCM3EJzjOpO3Q',
    'IDENTIFY_USER': identify_user,
    'IDENTIFY_COMPANY': identify_company,
    'LOG_BODY': True,
    'DEBUG': True
}

app.wsgi_app = MoesifMiddleware(app.wsgi_app, moesif_settings)

# Define routes
@app.route('/gov/no_italy', methods=['GET'])
def no_italy():
  return jsonify({'success': True})

@app.route('/gov/company1', methods=['GET'])
def company1():
  return jsonify({'success': True})

@app.route('/gov/canada', methods=['GET'])
def canada():
  return jsonify({'success': True})

@app.route('/gov/cairo', methods=['GET'])
def cairo():
  return jsonify({'success': True})

@app.route('/gov/for_companies_in_japan_only', methods=['GET'])
def for_companies_in_japan_only():
  return jsonify({'success': True})

@app.route('/gov/random', methods=['GET'])
def random():
  return jsonify({'success': True})

@app.route('/gov/multiple_match', methods=['GET'])
def multiple_match():
  return jsonify({'success': True})

@app.route('/gov/no_germany_companies_allowed', methods=['GET'])
def no_germany_companies_allowed():
  return jsonify({'success': True})

@app.route('/gov/header_match', methods=['GET'])
def header_match():
  return jsonify({'success': True})

# Run the app
if __name__ == '__main__':
  app.run(debug=True)
