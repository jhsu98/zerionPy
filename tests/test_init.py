import zerionPy
import time
import pytest
from fixtures import server_admin_6, server_admin_8
import os
from dotenv import load_dotenv
load_dotenv()

def test_empty_init():
    with pytest.raises(TypeError):
        zerionPy.ifb.IFB()

def test_blank_init():
    with pytest.raises(ValueError):
        zerionPy.ifb.IFB('','','','','')

def test_invalid_region():
    with pytest.raises(ValueError):
        zerionPy.ifb.IFB('s','r', 'ck','cs',6)

def test_invalid_version():
    with pytest.raises(ValueError):
        zerionPy.ifb.IFB('s','us','ck','cs',1)

def test_init_v6():
    server = os.environ['SERVER']
    client_key = os.environ['CLIENT_KEY']
    client_secret = os.environ['CLIENT_SECRET']
    region = os.environ['REGION']

    api = zerionPy.ifb.IFB(server,region,client_key,client_secret,6)
    assert api.getAccessToken() is not None

def test_init_v8():
    server = os.environ['SERVER']
    client_key = os.environ['CLIENT_KEY']
    client_secret = os.environ['CLIENT_SECRET']
    region = os.environ['REGION']

    api = zerionPy.ifb.IFB(server,region,client_key,client_secret,8)
    assert api.getAccessToken() is not None

def test_getAccessToken6(server_admin_6):
    assert server_admin_6.getAccessToken() is not None

def test_getApiCount6(server_admin_6):
    assert server_admin_6.getApiCount() is not None

def test_getStartTime6(server_admin_6):
    assert server_admin_6.getStartTime() is not None

def test_getApiLifetime6(server_admin_6):
    assert server_admin_6.getApiLifetime() is not None

def test_getAccessTokenExpiration6(server_admin_6):
    assert server_admin_6.getAccessTokenExpiration() is not None

def test_getAccessToken8(server_admin_8):
    assert server_admin_8.getAccessToken() is not None

def test_getApiCount8(server_admin_8):
    assert server_admin_8.getApiCount() is not None

def test_getStartTime8(server_admin_8):
    assert server_admin_8.getStartTime() is not None

def test_getApiLifetime8(server_admin_8):
    assert server_admin_8.getApiLifetime() is not None

def test_getAccessTokenExpiration8(server_admin_8):
    assert server_admin_8.getAccessTokenExpiration() is not None