import re
import inspect
import time
import re
import jwt
import requests
import json
from pprint import pprint

import logging
logging.basicConfig(filename='app.log', level=logging.DEBUG, format='%(asctime)s - %(message)s', datefmt='%d-%b-%y %H:%M:%S')

class ifbResponse():
    def __init__(self, headers, status_code, response):
        self.headers = headers
        self.status_code = status_code
        self.response = response

    def __str__(self):
        return str(self.status_code)

    def __repr__(self):
        return str(self.status_code)

    def __iter__(self):
        for item in self.response:
            yield item

class IFB():
    def __init__(self, server:str, region:str, client_key:str, client_secret:str, version:float, simple_response:bool=False, skip_rate_limit_retry:bool=False):
        if not all((server, client_key, client_secret, version, region)):
            raise ValueError("Invalid parameter values")

        if version not in (6, 8, 8.1):
            raise ValueError("Invalid version")

        if region not in ('us','uk','au','hipaa','qa'):
            raise ValueError("Invalid region")

        self.__server = server
        self.__client_key = client_key
        self.__client_secret = client_secret
        self.__version = version
        self.__region = region
        self.__isSimpleResponse = simple_response
        self.__isSkipRateLimitRetry = skip_rate_limit_retry
        self.__isZIM = "." in client_key

        self.__api_calls = 0
        self.__access_token = None
        self.__access_token_expiration = None
        self.__start_time = time.time()

        self.__session = requests.Session()
        self.__session.headers.update({ 'Content-Type': 'application/json' })

        try:
            match self.__version >= 8:
                case True:
                    self.__host = f'https://{self.__region + "-" if self.__region != "us" else ""}api.iformbuilder.com/exzact/api/v{int(self.__version * 10)}/{self.__server}'
                    self.__token_url = f'https://{self.__region + "-" if self.__region != "us" else ""}api.iformbuilder.com/exzact/api/v{int(self.__version * 10)}/{self.__server}/oauth/token'
                case False:
                    self.__host = f'https://{self.__server}.iformbuilder.com/exzact/api/v60'
                    self.__token_url = f'https://{self.__server}.iformbuilder.com/exzact/api/oauth/token'
            
            if self.__isZIM:
                self.__token_url = "https://qa-identity.zerionsoftware.com/oauth2/token" if self.__region == "qa" else "https://identity.zerionsoftware.com/oauth2/token"

            self.__requestAccessToken()
        except Exception as e:
            print(e)

    def __requestAccessToken(self):
        """Create JWT and request iFormBuilder Access Token
        If Token is successfully returned, store in session header
        Else null token is stored in session header
        """
        try:
            jwt_payload = {
                'iss': self.__client_key,
                'aud': self.__token_url,
                'iat': time.time(),
                'exp': time.time() + 300
            }

            encoded_jwt = jwt.encode(jwt_payload, self.__client_secret, algorithm='HS256')
            token_body = {
                'grant_type': 'urn:ietf:params:oauth:grant-type:jwt-bearer',
                'assertion': encoded_jwt
            }

            token_request = requests.post(self.__token_url, data=token_body, timeout=5)
            token_request.raise_for_status()
        except Exception as e:
            print(e)
        else:
            if not token_request.json().get('access_token'):
                raise ValueError("Access token not granted")

            self.__access_token = token_request.json().get('access_token')
            self.__session.headers.update({ 'Authorization': f'Bearer {self.__access_token}'})
            self.__access_token_expiration = time.time() + 3300

    def getAccessToken(self):
        return self.__access_token

    def getApiCount(self):
        return self.__api_calls

    def getStartTime(self):
        return self.__start_time

    def getApiLifetime(self):
        return round(time.time() - self.__start_time, 2)

    def getAccessTokenExpiration(self):
        return self.__access_token_expiration

    def getLastExecutionTime(self):
        return self.__last_execution_time

    def __parseFunctionName(self, s):
        parts = re.split('([A-Z][^A-Z]*)', s)
        return (parts[0], ''.join(parts[1:]))

    def __request(self, functionName:str, ids:tuple=(), body=None, params=None):
        method, resource = self.__parseFunctionName(functionName)

        match len(ids) > 0:
            case True:
                url = f'{self.__host}/{self.__resources[resource] % ids}'
            case False:
                url = f'{self.__host}/{self.__resources[resource]}'

        if self.__access_token is not None and time.time() > self.__access_token_expiration:
            self.__requestAccessToken()

        while True:
            result = self.__session.request(method, url, data=json.dumps(body), params=params)

            self.__api_calls += 1
            self.__last_execution_time = result.elapsed

            if result.status_code != 429 or self.__isSkipRateLimitRetry:
                if self.__isSimpleResponse:
                    return result.json()
                else:
                    return ifbResponse(result.headers, result.status_code, result.json())
            else:
                print('Request rate limited, waiting 60 seconds then retrying...')
                time.sleep(60)

    __resources = {
        "Profiles": "profiles",
        "Profile": "profiles/%s",
        "HomeProfile": "profiles/self",

        "CompanyInfo": "profiles/%s/company_info",

        "Users": "profiles/%s/users",
        "User": "profiles/%s/users/%s",

        "UserPageAssignments": "profiles/%s/users/%s/page_assignments",
        "UserPageAssignment": "profiles/%s/users/%s/page_assignments/%s",

        "UserRecordAssignments": "profiles/%s/users/%s/record_assignments",
        "UserRecordAssignment": "profiles/%s/users/%s/record_assignments/%s",

        "UserGroups": "profiles/%s/user_groups",
        "UserGroup": "profiles/%s/user_groups/%s",

        "UserGroupUserAssignments": "profiles/%s/user_groups/%s/users",
        "UserGroupUserAssignment": "profiles/%s/user_groups/%s/users/%s",

        "UserGroupPageAssignments": "profiles/%s/user_groups/%s/page_assignments",
        "UserGroupPageAssignment": "profiles/%s/user_groups/%s/page_assignments/%s",

        "Pages": "profiles/%s/pages",
        "Page": "profiles/%s/pages/%s",

        "PageFeed": "profiles/%s/pages/%s/feed",

        "PageLocalizations": "profiles/%s/pages/%s/localizations",
        "PageLocalization": "profiles/%s/pages/%s/localizations/%s",

        "PageUserAssignments": "profiles/%s/pages/%s/assignments",
        "PageUserAssignment": "profiles/%s/pages/%s/assignments/%s",

        "PageRecordAssignments": "profiles/%s/pages/%s/record_assignments",
        "PageRecordAssignment": "profiles/%s/pages/%s/record_assignments/%s",

        "PageEndpoints": "profiles/%s/pages/%s/http_callbacks",
        "PageEndpoint": "profiles/%s/pages/%s/http_callbacks/%s",

        "PageEmailAlerts": "profiles/%s/pages/%s/email_alerts",

        "PageTriggerPost": "profiles/%s/pages/%s/trigger_posts",

        "PageShares": "profiles/%s/pages/%s/shared_page",

        "PageDynamicAttributes": "profiles/%s/pages/%s/dynamic_attributes",
        "PageDynamicAttribute": "profiles/%s/pages/%s/dynamic_attributes/%s",

        "PageGroups": "profiles/%s/page_groups",
        "PageGroup": "profiles/%s/page_groups/%s",

        "PageGroupPageAssignments": "profiles/%s/page_groups/%s/pages",
        "PageGroupPageAssignment": "profiles/%s/page_groups/%s/pages/%s",

        "PageGroupUserAssignments": "profiles/%s/page_groups/%s/assignments",
        "PageGroupUserAssignment": "profiles/%s/page_groups/%s/assignments/%s",

        "Elements": "profiles/%s/pages/%s/elements",
        "Element": "profiles/%s/pages/%s/elements/%s",

        "ElementLocalizations": "profiles/%s/pages/%s/elements/%s/localizations",
        "ElementLocalization": "profiles/%s/pages/%s/elements/%s/localizations/%s",

        "ElementDynamicAttributes": "profiles/%s/pages/%s/elements/%s/dynamic_attributes",
        "ElementDynamicAttribute": "profiles/%s/pages/%s/elements/%s/dynamic_attributes/%s",

        "OptionLists": "profiles/%s/optionlists",
        "OptionList": "profiles/%s/optionlists/%s",

        "Options": "profiles/%s/optionlists/%s/options",
        "Option": "profiles/%s/optionlists/%s/options/%s",

        "OptionLocalizations": "profiles/%s/optionlists/%s/options/%s/localizations",
        "OptionLocalization": "profiles/%s/optionlists/%s/options/%s/localizations/%s",

        "Records": "profiles/%s/pages/%s/records",
        "Record": "profiles/%s/pages/%s/records/%s",

        "RecordAssignments": "profiles/%s/pages/%s/records/%s/assignments",
        "RecordAssignment": "profiles/%s/pages/%s/records/%s/assignments/%s",

        "Notifications": "profiles/%s/notifications",

        "PrivateMedia": "profiles/%s/media",

        "DeviceLicenses": "profiles/%s/licenses",
        "DeviceLicense": "profiles/%s/licenses/%s",
    }

    ##############################
    # Profiles
    ##############################
    def getProfiles(self, params=None):
        return self.__request(inspect.currentframe().f_code.co_name, params=params)

    def getProfile(self, profile_id):
        return self.__request(inspect.currentframe().f_code.co_name, ids=(profile_id,))

    def getHomeProfile(self):
        return self.__request(inspect.currentframe().f_code.co_name)

    def postProfile(self, body):
        return self.__request(f'{inspect.currentframe().f_code.co_name}s', body=body)

    def putProfile(self, profile_id, body):
        return self.__request(inspect.currentframe().f_code.co_name, ids=(profile_id,), body=body)

    ##############################
    # CompanyInfo
    ##############################
    def getCompanyInfo(self, profile_id, params=None):
        return self.__request(inspect.currentframe().f_code.co_name, ids=(profile_id, ), params=params)

    def putCompanyInfo(self, profile_id, body):
        return self.__request(inspect.currentframe().f_code.co_name, ids=(profile_id, ), body=body)

    ##############################
    # Users
    ##############################
    def getUsers(self, profile_id, params=None):
        return self.__request(inspect.currentframe().f_code.co_name, ids=(profile_id, ), params=params)

    def getUser(self, profile_id, user_id):
        return self.__request(inspect.currentframe().f_code.co_name, ids=(profile_id, user_id))

    def postUsers(self, profile_id, body):
        return self.__request(inspect.currentframe().f_code.co_name, ids=(profile_id, ), body=body)

    def putUsers(self, profile_id, body, params=None):
        return self.__request(inspect.currentframe().f_code.co_name, ids=(profile_id, ), body=body, params=params)

    def putUser(self, profile_id, user_id, body):
        return self.__request(inspect.currentframe().f_code.co_name, ids=(profile_id, user_id), body=body)

    def deleteUsers(self, profile_id, params=None):
        return self.__request(inspect.currentframe().f_code.co_name, ids=(profile_id, ), params=params)

    def deleteUser(self, profile_id, user_id):
        return self.__request(inspect.currentframe().f_code.co_name, ids=(profile_id, user_id))

    ##############################
    # UserPageAssignments
    ##############################
    def getUserPageAssignments(self, profile_id, user_id, params=None):
        return self.__request(inspect.currentframe().f_code.co_name, ids=(profile_id, user_id), params=params)

    def getUserPageAssignment(self, profile_id, user_id, page_id):
        return self.__request(inspect.currentframe().f_code.co_name, ids=(profile_id, user_id, page_id))

    def postUserPageAssignments(self, profile_id, user_id, body):
        return self.__request(inspect.currentframe().f_code.co_name, ids=(profile_id, user_id), body=body)

    def putUserPageAssignments(self, profile_id, user_id, body, params=None):
        return self.__request(inspect.currentframe().f_code.co_name, ids=(profile_id, user_id), body=body, params=params)

    def putUserPageAssignment(self, profile_id, user_id, page_id, body):
        return self.__request(inspect.currentframe().f_code.co_name, ids=(profile_id, user_id, page_id), body=body)

    def deleteUserPageAssignments(self, profile_id, user_id, params=None):
        return self.__request(inspect.currentframe().f_code.co_name, ids=(profile_id, user_id), params=params)

    def deleteUserPageAssignment(self, profile_id, user_id, page_id):
        return self.__request(inspect.currentframe().f_code.co_name, ids=(profile_id, user_id, page_id))

    ##############################
    # UserRecordAssignments
    ##############################
    def getUserRecordAssignments(self, profile_id, user_id, params=None):
        return self.__request(inspect.currentframe().f_code.co_name, ids=(profile_id, user_id), params=params)

    def getUserRecordAssignment(self, profile_id, user_id, record_id):
        return self.__request(inspect.currentframe().f_code.co_name, ids=(profile_id, user_id, record_id))

    def postUserRecordAssignments(self, profile_id, user_id, body):
        return self.__request(inspect.currentframe().f_code.co_name, ids=(profile_id, user_id), body=body)

    def deleteUserRecordAssignments(self, profile_id, user_id, params=None):
        return self.__request(inspect.currentframe().f_code.co_name, ids=(profile_id, user_id), params=params)

    def deleteUserRecordAssignment(self, profile_id, user_id, record_id):
        return self.__request(inspect.currentframe().f_code.co_name, ids=(profile_id, user_id, record_id))

    ##############################
    # UserGroups
    ##############################
    def getUserGroups(self, profile_id, params=None):
        return self.__request(inspect.currentframe().f_code.co_name, ids=(profile_id, ), params=params)

    def getUserGroup(self, profile_id, usergroup_id):
        return self.__request(inspect.currentframe().f_code.co_name, ids=(profile_id, usergroup_id))

    def postUserGroups(self, profile_id, body):
        return self.__request(inspect.currentframe().f_code.co_name, ids=(profile_id, ), body=body)

    def putUserGroup(self, profile_id, usergroup_id, body):
        return self.__request(inspect.currentframe().f_code.co_name, ids=(profile_id, usergroup_id), body=body)

    def deleteUserGroup(self, profile_id, usergroup_id):
        return self.__request(inspect.currentframe().f_code.co_name, ids=(profile_id, usergroup_id))

    ##############################
    # UserGroupUserAssignments
    ##############################
    def getUserGroupUserAssignments(self, profile_id, usergroup_id, params=None):
        return self.__request(inspect.currentframe().f_code.co_name, ids=(profile_id, usergroup_id), params=params)

    def getUserGroupUserAssignment(self, profile_id, usergroup_id, user_id):
        return self.__request(inspect.currentframe().f_code.co_name, ids=(profile_id, usergroup_id, user_id))

    def postUserGroupUserAssignments(self, profile_id, usergroup_id, body):
        return self.__request(inspect.currentframe().f_code.co_name, ids=(profile_id, usergroup_id), body=body)

    # def putUserGroupUserAssignments(self, profile_id, usergroup_id, body, params=None):
    #     return self.__request(inspect.currentframe().f_code.co_name, ids=(profile_id, usergroup_id), body=body, params=params)

    # def putUserGroupUserAssignment(self, profile_id, usergroup_id, user_id, body):
    #     return self.__request(inspect.currentframe().f_code.co_name, ids=(profile_id, usergroup_id, user_id), body=body)

    def deleteUserGroupUserAssignments(self, profile_id, usergroup_id, params=None):
        return self.__request(inspect.currentframe().f_code.co_name, ids=(profile_id, usergroup_id), params=params)

    def deleteUserGroupUserAssignment(self, profile_id, usergroup_id, user_id):
        return self.__request(inspect.currentframe().f_code.co_name, ids=(profile_id, usergroup_id, user_id))

    ##############################
    # UserGroupPageAssignments
    ##############################
    def getUserGroupPageAssignments(self, profile_id, usergroup_id, params=None):
        return self.__request(inspect.currentframe().f_code.co_name, ids=(profile_id, usergroup_id), params=params)

    def getUserGroupPageAssignment(self, profile_id, usergroup_id, page_id):
        return self.__request(inspect.currentframe().f_code.co_name, ids=(profile_id, usergroup_id, page_id))

    def postUserGroupPageAssignments(self, profile_id, usergroup_id, body):
        return self.__request(inspect.currentframe().f_code.co_name, ids=(profile_id, usergroup_id), body=body)

    def putUserGroupPageAssignments(self, profile_id, usergroup_id, body, params=None):
        return self.__request(inspect.currentframe().f_code.co_name, ids=(profile_id, usergroup_id), body=body, params=params)

    def putUserGroupPageAssignment(self, profile_id, usergroup_id, page_id, body):
        return self.__request(inspect.currentframe().f_code.co_name, ids=(profile_id, usergroup_id, page_id), body=body)

    def deleteUserGroupPageAssignments(self, profile_id, usergroup_id, params=None):
        return self.__request(inspect.currentframe().f_code.co_name, ids=(profile_id, usergroup_id), params=params)

    def deleteUserGroupPageAssignment(self, profile_id, usergroup_id, page_id):
        return self.__request(inspect.currentframe().f_code.co_name, ids=(profile_id, usergroup_id, page_id))

    ##############################
    # Pages
    ##############################
    def getPages(self, profile_id, params=None):
        return self.__request(inspect.currentframe().f_code.co_name, ids=(profile_id, ), params=params)

    def getPage(self, profile_id, page_id):
        return self.__request(inspect.currentframe().f_code.co_name, ids=(profile_id, page_id))

    def copyPage(self, profile_id, page_id):
        return self.__request(inspect.currentframe().f_code.co_name, ids=(profile_id, page_id))

    def postPages(self, profile_id, body):
        return self.__request(inspect.currentframe().f_code.co_name, ids=(profile_id, ), body=body)

    def putPage(self, profile_id, page_id, body):
        return self.__request(inspect.currentframe().f_code.co_name, ids=(profile_id, page_id), body=body)

    def deletePage(self, profile_id, page_id):
        return self.__request(inspect.currentframe().f_code.co_name, ids=(profile_id, page_id))

    ##############################
    # PageFeed
    ##############################
    def getPageFeed(self, profile_id, page_id, params=None):
        return self.__request(inspect.currentframe().f_code.co_name, ids=(profile_id, page_id), params=params)

    ##############################
    # PageLocalizations
    ##############################
    def getPageLocalizations(self, profile_id, page_id, params=None):
        return self.__request(inspect.currentframe().f_code.co_name, ids=(profile_id, page_id), params=params)

    def getPageLocalization(self, profile_id, page_id, language_code):
        return self.__request(inspect.currentframe().f_code.co_name, ids=(profile_id, page_id, language_code))

    def postPageLocalizations(self, profile_id, page_id, body):
        return self.__request(inspect.currentframe().f_code.co_name, ids=(profile_id, page_id), body=body)

    def putPageLocalizations(self, profile_id, page_id, body, params=None):
        return self.__request(inspect.currentframe().f_code.co_name, ids=(profile_id, page_id), body=body, params=params)

    def putPageLocalization(self, profile_id, page_id, language_code, body):
        return self.__request(inspect.currentframe().f_code.co_name, ids=(profile_id, page_id, language_code), body=body)

    def deletePageLocalizations(self, profile_id, page_id, params=None):
        return self.__request(inspect.currentframe().f_code.co_name, ids=(profile_id, page_id), params=params)

    def deletePageLocalization(self, profile_id, page_id, language_code):
        return self.__request(inspect.currentframe().f_code.co_name, ids=(profile_id, page_id, language_code))

    ##############################
    # PageUserAssignments
    ##############################
    def getPageUserAssignments(self, profile_id, page_id, params=None):
        return self.__request(inspect.currentframe().f_code.co_name, ids=(profile_id, page_id), params=params)

    def getPageUserAssignments(self, profile_id, page_id, user_id):
        return self.__request(inspect.currentframe().f_code.co_name, ids=(profile_id, page_id, user_id))

    def postPageUserAssignments(self, profile_id, page_id, body):
        return self.__request(inspect.currentframe().f_code.co_name, ids=(profile_id, page_id), body=body)
    
    def putPageUserAssignments(self, profile_id, page_id, body, params=None):
        return self.__request(inspect.currentframe().f_code.co_name, ids=(profile_id, page_id), body=body, params=params)

    def putPageUserAssignment(self, profile_id, page_id, user_id, body):
        return self.__request(inspect.currentframe().f_code.co_name, ids=(profile_id, page_id, user_id), body=body)

    def deletePageUserAssignments(self, profile_id, page_id, params=None):
        return self.__request(inspect.currentframe().f_code.co_name, ids=(profile_id, page_id), params=params)

    def deletePageUserAssignment(self, profile_id, page_id, user_id):
        return self.__request(inspect.currentframe().f_code.co_name, ids=(profile_id, page_id, user_id))

    ##############################
    # PageRecordAssignments
    ##############################
    def getPageRecordAssignments(self, profile_id, page_id, params=None):
        return self.__request(inspect.currentframe().f_code.co_name, ids=(profile_id, page_id), params=params)

    def deletePageRecordAssignments(self, profile_id, page_id, params=None):
        return self.__request(inspect.currentframe().f_code.co_name, ids=(profile_id, page_id), params=params)

    ##############################
    # PageEndpoints
    ##############################
    def getPageEndpoints(self, profile_id, page_id, params=None):
        return self.__request(inspect.currentframe().f_code.co_name, ids=(profile_id, page_id), params=params)

    def getPageEndpoint(self, profile_id, page_id, endpoint_id):
        return self.__request(inspect.currentframe().f_code.co_name, ids=(profile_id, page_id, endpoint_id))

    def postPageEndpoints(self, profile_id, page_id, body):
        return self.__request(inspect.currentframe().f_code.co_name, ids=(profile_id, page_id), body=body)

    def putPageEndpoint(self, profile_id, page_id, endpoint_id, body):
        return self.__request(inspect.currentframe().f_code.co_name, ids=(profile_id, page_id, endpoint_id), body=body)

    def deletePageEndpoints(self, profile_id, page_id, params=None):
        return self.__request(inspect.currentframe().f_code.co_name, ids=(profile_id, page_id), params=params)

    def deletePageEndpoint(self, profile_id, page_id, endpoint_id):
        return self.__request(inspect.currentframe().f_code.co_name, ids=(profile_id, page_id, endpoint_id))

    ##############################
    # PageEmailAlerts
    ##############################
    def getPageEmailAlerts(self, profile_id, page_id, params=None):
        return self.__request(inspect.currentframe().f_code.co_name, ids=(profile_id, page_id), params=params)

    def postPageEmailAlerts(self, profile_id, page_id, body):
        return self.__request(inspect.currentframe().f_code.co_name, ids=(profile_id, page_id), body=body)

    def deletePageEmailAlerts(self, profile_id, page_id, params=None):
        return self.__request(inspect.currentframe().f_code.co_name, ids=(profile_id, page_id), params=params)

    ##############################
    # PageTriggerPost
    ##############################
    def postPageTriggerPost(self, profile_id, page_id, body):
        return self.__request(inspect.currentframe().f_code.co_name, ids=(profile_id, page_id), body=body)

    ##############################
    # PageShares
    ##############################
    def getPageShares(self, profile_id, page_id, params=None):
        return self.__request(inspect.currentframe().f_code.co_name, ids=(profile_id, page_id), params=params)

    def postPageShares(self, profile_id, page_id, body):
        return self.__request(inspect.currentframe().f_code.co_name, ids=(profile_id, page_id), body=body)

    def putPageShares(self, profile_id, page_id, body, params=None):
        return self.__request(inspect.currentframe().f_code.co_name, ids=(profile_id, page_id), body=body, params=params)

    def deletePageShares(self, profile_id, page_id, params=None):
        return self.__request(inspect.currentframe().f_code.co_name, ids=(profile_id, page_id), params=params)

    ##############################
    # PageDynamicAttributes
    ##############################
    def getPageDynamicAttributes(self, profile_id, page_id, params=None):
        return self.__request(inspect.currentframe().f_code.co_name, ids=(profile_id, page_id), params=params)

    def getPageDynamicAttribute(self, profile_id, page_id, attribute_name):
        return self.__request(inspect.currentframe().f_code.co_name, ids=(profile_id, page_id, attribute_name))

    def postPageDynamicAttributes(self, profile_id, page_id, body):
        return self.__request(inspect.currentframe().f_code.co_name, ids=(profile_id, page_id), body=body)
    
    def putPageDynamicAttributes(self, profile_id, page_id, body, params=None):
        return self.__request(inspect.currentframe().f_code.co_name, ids=(profile_id, page_id), body=body, params=params)

    def putPageDynamicAttribute(self, profile_id, page_id, attribute_name, body):
        return self.__request(inspect.currentframe().f_code.co_name, ids=(profile_id, page_id, attribute_name), body=body)

    def deletePageDynamicAttributes(self, profile_id, page_id, params=None):
        return self.__request(inspect.currentframe().f_code.co_name, ids=(profile_id, page_id), params=params)

    def deletePageDynamicAttribute(self, profile_id, page_id, attribute_name):
        return self.__request(inspect.currentframe().f_code.co_name, ids=(profile_id, page_id, attribute_name))

    ##############################
    # PageGroups
    ##############################
    def getPageGroups(self, profile_id, params=None):
        return self.__request(inspect.currentframe().f_code.co_name, ids=(profile_id, ), params=params)

    def getPageGroup(self, profile_id, pagegroup_id):
        return self.__request(inspect.currentframe().f_code.co_name, ids=(profile_id, pagegroup_id))

    def postPageGroups(self, profile_id, body):
        return self.__request(inspect.currentframe().f_code.co_name, ids=(profile_id, ), body=body)

    def putPageGroup(self, profile_id, pagegroup_id, body):
        return self.__request(inspect.currentframe().f_code.co_name, ids=(profile_id, pagegroup_id), body=body)

    def deletePageGroup(self, profile_id, pagegroup_id):
        return self.__request(inspect.currentframe().f_code.co_name, ids=(profile_id, pagegroup_id))

    ##############################
    # PageGroupPageAssignments
    ##############################
    def getPageGroupPageAssignments(self, profile_id, pagegroup_id):
        return self.__request(inspect.currentframe().f_code.co_name, ids=(profile_id, pagegroup_id))

    def postPageGroupPageAssignments(self, profile_id, pagegroup_id, body):
        return self.__request(inspect.currentframe().f_code.co_name, ids=(profile_id, pagegroup_id), body=body)

    def deletePageGroupPageAssignments(self, profile_id, pagegroup_id, page_id, body):
        return self.__request(inspect.currentframe().f_code.co_name, ids=(profile_id, pagegroup_id, page_id), body=body)

    ##############################
    # PageGroupUserAssignments
    ##############################
    def getPageGroupUserAssignments(self, profile_id, pagegroup_id, params=None):
        return self.__request(inspect.currentframe().f_code.co_name, ids=(profile_id, pagegroup_id), params=params)

    def getPageGroupUserAssignment(self, profile_id, pagegroup_id, user_id):
        return self.__request(inspect.currentframe().f_code.co_name, ids=(profile_id, pagegroup_id, user_id))

    def postPageGroupUserAssignments(self, profile_id, pagegroup_id, body):
        return self.__request(inspect.currentframe().f_code.co_name, ids=(profile_id, pagegroup_id), body=body)
    
    def putPageGroupUserAssignments(self, profile_id, pagegroup_id, body, params=None):
        return self.__request(inspect.currentframe().f_code.co_name, ids=(profile_id, pagegroup_id), body=body, params=params)

    def putPageGroupUserAssignment(self, profile_id, pagegroup_id, user_id, body):
        return self.__request(inspect.currentframe().f_code.co_name, ids=(profile_id, pagegroup_id, user_id), body=body)

    def deletePageGroupUserAssignments(self, profile_id, pagegroup_id, params=None):
        return self.__request(inspect.currentframe().f_code.co_name, ids=(profile_id, pagegroup_id), params=params)

    def deletePageGroupUserAssignment(self, profile_id, pagegroup_id, user_id):
        return self.__request(inspect.currentframe().f_code.co_name, ids=(profile_id, pagegroup_id, user_id))

    ##############################
    # Elements
    ##############################
    def getElements(self, profile_id, page_id, params=None):
        return self.__request(inspect.currentframe().f_code.co_name, ids=(profile_id, page_id), params=params)

    def getElement(self, profile_id, page_id, element_id):
        return self.__request(inspect.currentframe().f_code.co_name, ids=(profile_id, page_id, element_id))

    def copyElement(self, profile_id, page_id, element_id):
        return self.__request(inspect.currentframe().f_code.co_name, ids=(profile_id, page_id, element_id))

    def postElements(self, profile_id, page_id, body):
        return self.__request(inspect.currentframe().f_code.co_name, ids=(profile_id, page_id), body=body)
    
    def putElements(self, profile_id, page_id, body, params=None):
        return self.__request(inspect.currentframe().f_code.co_name, ids=(profile_id, page_id), body=body, params=params)

    def putElement(self, profile_id, page_id, element_id, body):
        return self.__request(inspect.currentframe().f_code.co_name, ids=(profile_id, page_id, element_id), body=body)

    def deleteElements(self, profile_id, page_id, params=None):
        return self.__request(inspect.currentframe().f_code.co_name, ids=(profile_id, page_id), params=params)

    def deleteElement(self, profile_id, page_id, element_id):
        return self.__request(inspect.currentframe().f_code.co_name, ids=(profile_id, page_id, element_id))

    ##############################
    # ElementLocalizations
    ##############################
    def getElementLocalizations(self, profile_id, page_id, element_id, params=None):
        return self.__request(inspect.currentframe().f_code.co_name, ids=(profile_id, page_id, element_id), params=params)

    def getElementLocalization(self, profile_id, page_id, element_id, language_code):
        return self.__request(inspect.currentframe().f_code.co_name, ids=(profile_id, page_id, element_id, language_code))

    def postElementLocalizations(self, profile_id, page_id, element_id, body):
        return self.__request(inspect.currentframe().f_code.co_name, ids=(profile_id, page_id, element_id), body=body)
    
    def putElementLocalizations(self, profile_id, page_id, element_id, body, params=None):
        return self.__request(inspect.currentframe().f_code.co_name, ids=(profile_id, page_id, element_id), body=body, params=params)

    def putElementLocalization(self, profile_id, page_id, element_id, language_code, body, ):
        return self.__request(inspect.currentframe().f_code.co_name, ids=(profile_id, page_id, element_id, language_code), body=body)

    def deleteElementLocalizations(self, profile_id, page_id, element_id, params=None):
        return self.__request(inspect.currentframe().f_code.co_name, ids=(profile_id, page_id, element_id), params=params)

    def deleteElementLocalization(self, profile_id, page_id, element_id, language_code):
        return self.__request(inspect.currentframe().f_code.co_name, ids=(profile_id, page_id, element_id, language_code))

    ##############################
    # ElementDynamicAttributes
    ##############################
    def getElementDynamicAttributes(self, profile_id, page_id, element_id, params=None):
        return self.__request(inspect.currentframe().f_code.co_name, ids=(profile_id, page_id, element_id), params=params)

    def getElementDynamicAttribute(self, profile_id, page_id, element_id, attribute_name):
        return self.__request(inspect.currentframe().f_code.co_name, ids=(profile_id, page_id, element_id, attribute_name))

    def postElementDynamicAttributes(self, profile_id, page_id, element_id, body):
        return self.__request(inspect.currentframe().f_code.co_name, ids=(profile_id, page_id, element_id), body=body)
    
    def putElementDynamicAttributes(self, profile_id, page_id, element_id, body, params=None):
        return self.__request(inspect.currentframe().f_code.co_name, ids=(profile_id, page_id, element_id), body=body, params=params)

    def putElementDynamicAttribute(self, profile_id, page_id, element_id, attribute_name, body):
        return self.__request(inspect.currentframe().f_code.co_name, ids=(profile_id, page_id, element_id, attribute_name), body=body)

    def deleteElementDynamicAttributes(self, profile_id, page_id, element_id, params=None):
        return self.__request(inspect.currentframe().f_code.co_name, ids=(profile_id, page_id, element_id), params=params)

    def deleteElementDynamicAttribute(self, profile_id, page_id, element_id, attribute_name):
        return self.__request(inspect.currentframe().f_code.co_name, ids=(profile_id, page_id, element_id, attribute_name))

    ##############################
    # OptionLists
    ##############################
    def getOptionLists(self, profile_id, params=None):
        return self.__request(inspect.currentframe().f_code.co_name, ids=(profile_id, ), params=params)

    def getOptionList(self, profile_id, optionlist_id):
        return self.__request(inspect.currentframe().f_code.co_name, ids=(profile_id, optionlist_id))

    def copyOptionList(self, profile_id, optionlist_id):
        return self.__request(inspect.currentframe().f_code.co_name, ids=(profile_id, optionlist_id))

    def postOptionLists(self, profile_id, body):
        return self.__request(inspect.currentframe().f_code.co_name, ids=(profile_id, ), body=body)
    
    def putOptionList(self, profile_id, optionlist_id, body):
        return self.__request(inspect.currentframe().f_code.co_name, ids=(profile_id, optionlist_id), body=body)

    def deleteOptionList(self, profile_id, optionlist_id):
        return self.__request(inspect.currentframe().f_code.co_name, ids=(profile_id, optionlist_id))

    ##############################
    # Options
    ##############################
    def getOptions(self, profile_id, optionlist_id, params=None):
        return self.__request(inspect.currentframe().f_code.co_name, ids=(profile_id, optionlist_id), params=params)

    def getOption(self, profile_id, optionlist_id, option_id):
        return self.__request(inspect.currentframe().f_code.co_name, ids=(profile_id, optionlist_id, option_id))

    def postOptions(self, profile_id, optionlist_id, body):
        return self.__request(inspect.currentframe().f_code.co_name, ids=(profile_id, optionlist_id), body=body)

    def putOptions(self, profile_id, optionlist_id, body, params=None):
        return self.__request(inspect.currentframe().f_code.co_name, ids=(profile_id, optionlist_id), body=body, params=params)

    def putOption(self, profile_id, optionlist_id, option_id, body):
        return self.__request(inspect.currentframe().f_code.co_name, ids=(profile_id, optionlist_id, option_id), body=body)

    def deleteOptions(self, profile_id, optionlist_id, params=None):
        return self.__request(inspect.currentframe().f_code.co_name, ids=(profile_id, optionlist_id), params=params)

    def deleteOption(self, profile_id, optionlist_id, option_id):
        return self.__request(inspect.currentframe().f_code.co_name, ids=(profile_id, optionlist_id, option_id))

    ##############################
    # OptionLocalizations
    ##############################
    def getOptionLocalizations(self, profile_id, optionlist_id, option_id, params=None):
        return self.__request(inspect.currentframe().f_code.co_name, ids=(profile_id, optionlist_id, option_id), params=params)

    def getOptionLocalization(self, profile_id, optionlist_id, option_id, language_code):
        return self.__request(inspect.currentframe().f_code.co_name, ids=(profile_id, optionlist_id, option_id, language_code))

    def postOptionLocalizations(self, profile_id, optionlist_id, option_id, body):
        return self.__request(inspect.currentframe().f_code.co_name, ids=(profile_id, optionlist_id, option_id), body=body)
    
    def putOptionLocalizations(self, profile_id, optionlist_id, option_id, body, params=None):
        return self.__request(inspect.currentframe().f_code.co_name, ids=(profile_id, optionlist_id, option_id), body=body, params=params)

    def putOptionLocalization(self, profile_id, optionlist_id, option_id, language_code, body):
        return self.__request(inspect.currentframe().f_code.co_name, ids=(profile_id, optionlist_id, option_id, language_code), body=body)

    def deleteOptionLocalizations(self, profile_id, optionlist_id, option_id, params=None):
        return self.__request(inspect.currentframe().f_code.co_name, ids=(profile_id, optionlist_id, option_id), params=params)

    def deleteOptionLocalization(self, profile_id, optionlist_id, option_id, language_code):
        return self.__request(inspect.currentframe().f_code.co_name, ids=(profile_id, optionlist_id, option_id, language_code))

    ##############################
    # Records
    ##############################
    def getRecords(self, profile_id, page_id, params=None):
        return self.__request(inspect.currentframe().f_code.co_name, ids=(profile_id, page_id), params=params)

    def getRecord(self, profile_id, page_id, record_id):
        return self.__request(inspect.currentframe().f_code.co_name, ids=(profile_id, page_id, record_id))

    def copyRecord(self, profile_id, page_id, record_id):
        return self.__request(inspect.currentframe().f_code.co_name, ids=(profile_id, page_id, record_id))

    def postRecords(self, profile_id, page_id, body):
        return self.__request(inspect.currentframe().f_code.co_name, ids=(profile_id, page_id), body=body)

    def putRecords(self, profile_id, page_id, body, params=None):
        return self.__request(inspect.currentframe().f_code.co_name, ids=(profile_id, page_id), body=body, params=params)

    def putRecord(self, profile_id, page_id, record_id, body):
        return self.__request(inspect.currentframe().f_code.co_name, ids=(profile_id, page_id, record_id), body=body)

    def deleteRecords(self, profile_id, page_id, params=None):
        return self.__request(inspect.currentframe().f_code.co_name, ids=(profile_id, page_id), params=params)

    def deleteRecord(self, profile_id, page_id, record_id):
        return self.__request(inspect.currentframe().f_code.co_name, ids=(profile_id, page_id, record_id))

    ##############################
    # RecordAssignments
    ##############################
    def getRecordAssignments(self, profile_id, page_id, record_id, params=None):
        return self.__request(inspect.currentframe().f_code.co_name, ids=(profile_id, page_id, record_id), params=params)

    def getRecordAssignment(self, profile_id, page_id, record_id, assignment_id):
        return self.__request(inspect.currentframe().f_code.co_name, ids=(profile_id, page_id, record_id, assignment_id))

    def postRecordAssignments(self, profile_id, page_id, record_id, body):
        return self.__request(inspect.currentframe().f_code.co_name, ids=(profile_id, page_id, record_id), body=body)
    
    def deleteRecordAssignments(self, profile_id, page_id, record_id, params=None):
        return self.__request(inspect.currentframe().f_code.co_name, ids=(profile_id, page_id, record_id), params=params)

    def deleteRecordAssignment(self, profile_id, page_id, record_id, assignment_id):
        return self.__request(inspect.currentframe().f_code.co_name, ids=(profile_id, page_id, record_id, assignment_id))

    ##############################
    # Notifications
    ##############################
    def postNotifications(self, profile_id, body):
        return self.__request(inspect.currentframe().f_code.co_name, ids=(profile_id, ), body=body)

    ##############################
    # PrivateMedia
    ##############################
    def getPrivateMedia(self, profile_id, media_url):
        return self.__request(inspect.currentframe().f_code.co_name, ids=(profile_id, ), params={'URL': media_url})

    ##############################
    # DeviceLicenses
    ##############################
    def getDeviceLicenses(self, profile_id, params=None):
        return self.__request(inspect.currentframe().f_code.co_name, ids=(profile_id, ), params=params)

    def getDeviceLicense(self, profile_id, license_id):
        return self.__request(inspect.currentframe().f_code.co_name, ids=(profile_id, license_id))