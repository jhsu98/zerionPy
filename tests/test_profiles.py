import zerionPy
import time
import pytest
from fixtures import server_admin_6, server_admin_8
import os
from dotenv import load_dotenv
load_dotenv()

PROFILE_ID = int(os.environ['PROFILE_ID'])
HOME_PROFILE_ID = int(os.environ['HOME_PROFILE_ID'])

def test_getProfiles6(server_admin_6):
    result = server_admin_6.getProfiles()
    assert result.status_code == 200

def test_getProfiles8(server_admin_8):
    result = server_admin_8.getProfiles()
    assert result.status_code == 200

def test_getProfilesWithGrammar6(server_admin_6):
    result = server_admin_6.getProfiles({'fields': 'id((="1")&(!="1"))'})
    assert len(result.response) == 0

def test_getProfilesWithGrammar8(server_admin_8):
    result = server_admin_8.getProfiles({'fields': 'id(="1")'})
    assert result.status_code == 200

def test_getProfile6(server_admin_6):
    result = server_admin_6.getProfile(PROFILE_ID)
    assert result.status_code == 200

def test_getProfile8(server_admin_8):
    result = server_admin_8.getProfile(PROFILE_ID)
    assert result.status_code == 200

def test_getHomeProfile6(server_admin_6):
    result = server_admin_6.getHomeProfile()
    assert result.response['id'] == HOME_PROFILE_ID

def test_getHomeProfile8(server_admin_8):
    result = server_admin_8.getHomeProfile()
    assert result.response['id'] == HOME_PROFILE_ID