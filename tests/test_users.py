import zerionPy
import time
import pytest
from fixtures import server_admin_6, server_admin_8
import os
from dotenv import load_dotenv
load_dotenv()

PROFILE_ID = os.environ['PROFILE_ID']

def test_getUsers6(server_admin_6):
    result = server_admin_6.getUsers(PROFILE_ID)
    assert result.status_code == 200

def test_getUsers8(server_admin_8):
    result = server_admin_8.getUsers(PROFILE_ID)
    assert result.status_code == 200

def test_getUsersWithGrammar6(server_admin_6):
    result = server_admin_6.getUsers(PROFILE_ID, {'fields': 'id(>"1")'})
    assert result.status_code == 200

def test_getUsersWithGrammar8(server_admin_8):
    result = server_admin_8.getUsers(PROFILE_ID, {'fields': 'id(>"1")'})
    assert result.status_code == 200

def test_getUserGroups6(server_admin_6):
    result = server_admin_6.getUserGroups(PROFILE_ID)
    assert result.status_code == 200

def test_getUserGroups8(server_admin_8):
    result = server_admin_8.getUserGroups(PROFILE_ID)
    assert result.status_code == 200

def test_crudUser(server_admin_6, server_admin_8):
    def crudUser(api):
        errors = []
        user_id = None

        try:
            result = api.postUsers(
                PROFILE_ID, {
                    'username': f'u{int(time.time())}',
                    'password': 'Letmein1!',
                    'email': 'test@test.com'
                }
            )

            if result.status_code != 201:
                errors.append(f'postUsers <{result.status_code}>: {result.response}')
                
            user_id = result.response['id']

            result = api.putUser(
                PROFILE_ID,
                user_id,
                {
                    'first_name': 'Cloud',
                }
            )

            if result.status_code != 200:
                errors.append(f'putUser <{result.status_code}>: {result.response}')

            result = api.getUser(
                PROFILE_ID,
                user_id
            )

            if result.status_code != 200:
                errors.append(f'getUser <{result.status_code}>: {result.response}')

            if result.response['first_name'] != 'Cloud':
                errors.append('Name did not update from PUT')

            result = api.deleteUser(PROFILE_ID, user_id)

            if result.status_code != 200:
                errors.append(f'deleteUser <{result.status_code}>: {result.response}')
        except Exception as e:
            errors.append(e)

            if user_id:
                api.deleteUser(PROFILE_ID, user_id)

        return errors

    fixtures = {
        'server_admin_6': server_admin_6, 
        'server_admin_8': server_admin_8
    }

    failures = dict()

    for fixture in fixtures:
        result = crudUser(server_admin_6)

        if result:
            failures[fixture] = result

    assert failures == dict()

def test_crudUsergroup(server_admin_6, server_admin_8):
    def crudUserGroup(api):
        errors = []
        usergroup_id = None

        try:
            result = api.postUserGroups(
                PROFILE_ID, {
                    'name': f'g{int(time.time())}'
                }
            )

            if result.status_code != 201:
                errors.append(f'postUserGroups <{result.status_code}>: {result.response}')
                
            usergroup_id = result.response['id']

            result = api.putUserGroup(
                PROFILE_ID,
                usergroup_id,
                {
                    'name': 'the_returners',
                }
            )

            if result.status_code != 200:
                errors.append(f'putUserGroup <{result.status_code}>: {result.response}')

            result = api.getUserGroup(
                PROFILE_ID,
                usergroup_id
            )

            if result.status_code != 200:
                errors.append(f'getUserGroup <{result.status_code}>: {result.response}')

            if result.response['name'] != 'the_returners':
                errors.append('Name did not update from PUT')

            result = api.deleteUserGroup(PROFILE_ID, usergroup_id)

            if result.status_code != 200:
                errors.append(f'deleteUserGroup <{result.status_code}>: {result.response}')
        except Exception as e:
            errors.append(e)

            if usergroup_id:
                api.deleteUserGroup(PROFILE_ID, usergroup_id)

        return errors

    fixtures = {
        'server_admin_6': server_admin_6, 
        'server_admin_8': server_admin_8
    }

    failures = dict()

    for fixture in fixtures:
        result = crudUserGroup(server_admin_6)

        if result:
            failures[fixture] = result

    assert failures == dict()

