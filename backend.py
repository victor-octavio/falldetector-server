from flask import Flask, Response, jsonify
from flask_cors import CORS
import requests

app = Flask(__name__)
CORS(app)

@app.post('/notify')
def pipelineCall():
    try:
        requests.post('http://localhost:5678/webhook-test/queda', timeout=3)
    except:
        pass
    
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8090, debug=False)
