from datetime import datetime, timedelta
from flask import Flask, Response, request
import websocket
import multiprocessing
import os
from .token_store import TokenStore

PROXY_SERVER_PORT = 3580 if 'PROXY_SERVER_PORT' not in os.environ else os.environ['PROXY_SERVER_PORT']

app = Flask(__name__)
store = TokenStore()


def _validate_stream_async(stream_url, q):
    try:
        ws = websocket.create_connection(stream_url)
        ws.close()
    except Exception as e:
        print(e)
        q.put((False, "Unable to connect to stream. Details: '%s'" % str(e)))
    else:
        q.put((True, ""))


def _validate_stream(stream_url, timeout_sec=5):
    q = multiprocessing.Queue()
    process = multiprocessing.Process(target=_validate_stream_async, args=(stream_url, q))
    process.start()
    process.join(timeout_sec)
    if process.is_alive():
        process.terminate()
        return False, "Timeout while trying to connect to '%s'" % stream_url
    success, err_message = q.get()
    return success, err_message


@app.route('/token')
def get_token():
    stream_url = request.args.get('stream_url', type=str)
    expires_at = request.args.get('expires_at', type=datetime,
                                  default=datetime.now()+timedelta(minutes=2))
    if stream_url is None:
        return "You need to provide the URL of your stream.", 400

    test_status, error_message = _validate_stream(stream_url)
    if not test_status:
        return error_message, 500

    return store.register(stream_url, expires_at)


@app.route('/proxy')
def proxy_wss():
    token = request.args.get('token', type=str)
    if token is None:
        return "You need to provide a valid token to start proxying.", 400
    stream_url, expiration = store.get_token_attributes(token)
    if stream_url is None:
        return "Token '%s' is invalid. Please provide a valid token." % str(token), 401

    ws = websocket.create_connection(stream_url)

    def generate(webs):
        while expiration > datetime.now():
            yield webs.recv()
        webs.close()
    return Response(generate(ws), mimetype='text/plain')


@app.route('/info')
def info():
    return store.dump(), 200


def start():
    app.run('0.0.0.0', port=PROXY_SERVER_PORT)


def get_test_client():
    return app.test_client()


if __name__ == '__main__':
    start()