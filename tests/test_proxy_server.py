#  SPDX-License-Identifier: Apache-2.0
import pytest
from unittest import mock

from osmosis_streaming_driver.proxy_server.app import get_test_client

client = get_test_client()


def mocked_ws_connection(*args, **kwargs):
    class MockWebSocket:
        def __init__(self, stream_url):
            self.stream_url = stream_url

        def close(self):
            pass

        def recv(self):
            pass

    if args[0].endswith('wss://valid'):
        return MockWebSocket(args[0])

    raise Exception('Invalid stream')


def test_get_token_without_stream_url():
    assert client.get("/token").status_code == 400


@mock.patch('websocket.create_connection', side_effect=mocked_ws_connection)
def test_get_token_valid_stream(mock_ws):
    assert client.get("/token?stream_url=wss://valid").status_code == 200


@mock.patch('websocket.create_connection', side_effect=mocked_ws_connection)
def test_get_token_invalid_stream(mock_ws):
    assert client.get("/token?stream_url=wss://invalid").status_code == 500


@mock.patch('websocket.create_connection', side_effect=mocked_ws_connection)
def test_proxy_without_stream_url(mock_ws):
    assert client.get("/proxy").status_code == 400


def mocked_get_stream_url_from_token(*args, **kwargs):
    token = args[0]
    if token == 'valid':
        return "wss://valid"
    return None


@mock.patch('websocket.create_connection', side_effect=mocked_ws_connection)
@mock.patch('osmosis_streaming_driver.proxy_server.TokenStore.get_stream_url', side_effect=mocked_get_stream_url_from_token)
def test_proxy_valid_token(mock_ws, mock_get_stream_url):
    assert client.get("/proxy?token=valid").status_code == 200


@mock.patch('websocket.create_connection', side_effect=mocked_ws_connection)
@mock.patch('osmosis_streaming_driver.proxy_server.TokenStore.get_stream_url', side_effect=mocked_get_stream_url_from_token)
def test_proxy_invalid_token(mock_ws, mock_get_stream_url):
    assert client.get("/proxy?token=invalid").status_code == 401


