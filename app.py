import os
import time
import json
import requests
from flask import Flask, request, jsonify

app = Flask(__name__)

INSTANCE_URL = os.environ.get('INSTANCE_URL')
AGENT_ID     = os.environ.get('AGENT_ID')
ENV_ID       = os.environ.get('ENV_ID')
IBM_API_KEY  = os.environ.get('IBM_API_KEY')

def get_token():
    r = requests.post(
        'https://iam.cloud.ibm.com/identity/token',
        data={
            'grant_type': 'urn:ibm:params:oauth:grant-type:apikey',
            'apikey': IBM_API_KEY
        },
        headers={'Content-Type': 'application/x-www-form-urlencoded'}
    )
    if r.status_code != 200:
        return None
    return r.json().get('access_token')

def start_run(token, message, agent_id, env_id):
    r = requests.post(
        f'{INSTANCE_URL}/v1/orchestrate/runs?stream=false&multiple_content=true',
        headers={
            'Authorization': f'Bearer {token}',
            'Content-Type': 'application/json'
        },
        json={
            'message': {'role': 'user', 'content': message},
            'agent_id': agent_id,
            'environment_id': env_id
        }
    )
    if r.status_code != 200:
        print(f'Start run error: {r.status_code} {r.text}')
        return None
    return r.json().get('run_id')

def poll_for_answer(token, run_id, max_attempts=30, wait_seconds=3):
    for attempt in range(1, max_attempts + 1):
        time.sleep(wait_seconds)
        r = requests.get(
            f'{INSTANCE_URL}/v1/orchestrate/runs/{run_id}',
            headers={'Authorization': f'Bearer {token}'}
        )
        if r.status_code != 200:
            print(f'Poll error: {r.status_code} {r.text}')
            return None
        result = r.json()
        status = result.get('status', 'unknown')
        print(f'Attempt {attempt} — status: {status}')

        if status == 'completed':
            try:
                return result['result']['data']['message']['content'][0]['text']
            except (KeyError, IndexError) as e:
                print(f'Extraction error: {e}')
                return None

        if status in ['failed', 'error']:
            print(f'Run failed: {result}')
            return None

    print('Timed out.')
    return None

@app.route('/health', methods=['GET'])
def health():
    return jsonify({'status': 'ok'})

@app.route('/send', methods=['POST'])
def send():
    try:
        raw_body = request.get_data(as_text=True)
        print(f'RAW BODY: {raw_body}')
        print(f'CONTENT-TYPE: {request.content_type}')

        body = {}
        if request.is_json:
            body = request.get_json(force=True, silent=True) or {}
        if not body and request.form:
            body = request.form.to_dict()
        if not body and raw_body:
            try:
                body = json.loads(raw_body)
            except Exception:
                body = {'message': raw_body}

        message  = body.get('message', '')
        history  = body.get('history', '')
        agent_id = body.get('agent_id', AGENT_ID)
        env_id   = body.get('env_id', ENV_ID)

        # Combine history and current message for context
        full_message = f"{history}\nUser: {message}" if history else message

        if not full_message:
            return jsonify({'error': 'No message provided'}), 400

        token = get_token()
        if not token:
            return jsonify({'error': 'Could not retrieve IBM token'}), 500

        run_id = start_run(token, full_message, agent_id, env_id)
        if not run_id:
            return jsonify({'error': 'Could not start agent run'}), 500

        answer = poll_for_answer(token, run_id)
        if not answer:
            return 'No answer received from agent', 500

        return answer, 200, {'Content-Type': 'text/plain; charset=utf-8'}

    except Exception as e:
        print(f'Error: {e}')
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port)
