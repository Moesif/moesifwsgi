from flask import Flask, jsonify, request
from moesifwsgi import MoesifMiddleware

# Initialize Flask app
app = Flask(__name__)

# Moesif Middleware options
def identify_user(app, environ, response_headers=dict()):
  return environ.get('HTTP_X_USER_ID')

def identify_company(app, environ, response_headers=dict()):
  return environ.get('HTTP_X_COMPANY_ID')

moesif_settings = {
    'APPLICATION_ID': 'Your Moesif Application Id',
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
