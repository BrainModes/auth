import json
import unittest
import warnings
from unittest import mock

import keycloak
from keycloak import exceptions

from app import create_app
from config import ConfigSettings
from module_keycloak.ops_admin import OperationsAdmin
from module_keycloak.ops_user import OperationsUser

EXCEPTION_DATA = {
    "response_body": '{ "error": "error" }',
    "error_message": '{ "error": "error" }',
    "response_code": 500,
}


class UserTests(unittest.TestCase):
    AUTH_DATA = {
        "realm": ConfigSettings.KEYCLOAK_REALM,
        "username": "unittestuser",
        "password": "Testing123!",
    }

    def setUp(self):
        warnings.simplefilter("ignore", ResourceWarning)
        app = create_app()

        app.config['TESTING'] = True
        app.config['DEBUG'] = True
        self.app = app.test_client()

        operations_admin = OperationsAdmin(ConfigSettings.KEYCLOAK_REALM)
        try:
            # Delete the test user if it already exists
            operations_admin.delete_user("unittestuser")
        except keycloak.exceptions.KeycloakGetError:
            pass

        self.user = operations_admin.create_user(
            "unittestuser",
            "Testing123!",
            "unittesting@test.com",
            "Test",
            "User",
            cred_type="password",
            enabled=True
        )
        return super().setUp()

    def tearDown(self):
        operations_admin = OperationsAdmin(ConfigSettings.KEYCLOAK_REALM)
        operations_admin.delete_user(self.user)
        return super().tearDown()

    def test_docs(self):
        response = self.app.get('/v1/api-doc')
        print(response)
        self.assertEqual(response.status_code, 200)

    def test_user_auth(self):
        response = self.app.post('/v1/users/auth', json=self.AUTH_DATA)
        self.assertEqual(response.status_code, 200)
        response_json = json.loads(response.data)
        self.assertEqual(response_json["error_msg"], "")
        self.assertTrue(response_json["result"]["access_token"])

    def test_auth_missing(self):
        data = self.AUTH_DATA.copy()
        del data["password"]
        response = self.app.post('/v1/users/auth', json=data)
        self.assertEqual(response.status_code, 400)
        response_json = json.loads(response.data)
        self.assertEqual(response_json["result"], "Missing required information")

    @mock.patch.object(OperationsUser, '__init__',
                       side_effect=keycloak.exceptions.KeycloakAuthenticationError(**EXCEPTION_DATA))
    def test_auth_keycloakauth_exception(self, mock_data):
        response = self.app.post('/v1/users/auth', json=self.AUTH_DATA)
        self.assertEqual(response.status_code, 500)
        response_json = json.loads(response.data)
        self.assertEqual(response_json["result"]["error"], "error")

    @mock.patch.object(OperationsUser, '__init__', side_effect=keycloak.exceptions.KeycloakGetError(**EXCEPTION_DATA))
    def test_auth_keycloakget_exception(self, mock_data):
        response = self.app.post('/v1/users/auth', json=self.AUTH_DATA)
        self.assertEqual(response.status_code, 500)
        response_json = json.loads(response.data)
        self.assertEqual(response_json["result"]["error"], "error")

    @mock.patch.object(OperationsUser, '__init__', side_effect=Exception())
    def test_auth_exception(self, mock_data):
        response = self.app.post('/v1/users/auth', json=self.AUTH_DATA)
        self.assertEqual(response.status_code, 500)
        response_json = json.loads(response.data)
        print(response_json)
        self.assertEqual(response_json["result"], "User authentication failed : ")

    def test_user_refresh(self):
        response = self.app.post('/v1/users/auth', json=self.AUTH_DATA)
        self.assertEqual(response.status_code, 200)
        response_json = json.loads(response.data)
        refresh_data = {
            "realm": ConfigSettings.KEYCLOAK_REALM,
            "refreshtoken": response_json["result"]["refresh_token"]
        }
        response = self.app.post('/v1/users/refresh', json=refresh_data)
        self.assertEqual(response.status_code, 200)
        response_json = json.loads(response.data)
        self.assertEqual(response_json["error_msg"], "")
        self.assertTrue(response_json["result"]["refresh_token"])

    def test_user_refresh_missing(self):
        response = self.app.post('/v1/users/refresh')
        self.assertEqual(response.status_code, 400)
        response_json = json.loads(response.data)
        self.assertEqual(response_json["result"], "Missing refresh token")

    @mock.patch.object(OperationsUser, '__init__', side_effect=keycloak.exceptions.KeycloakGetError(**EXCEPTION_DATA))
    def test_refresh_keycloakget_exception(self, mock_data):
        refresh_data = {
            "realm": ConfigSettings.KEYCLOAK_REALM,
            "refreshtoken": "test"
        }
        response = self.app.post('/v1/users/refresh', json=refresh_data)
        self.assertEqual(response.status_code, 500)
        response_json = json.loads(response.data)
        self.assertEqual(response_json["result"], {"error": "error"})

    @unittest.skip("deprecated the APIs")
    def test_user_password(self):
        data = {
            "username": "unittestuser",
            "old_password": "Testing123!",
            "new_password": "Testing234!",
            "realm": ConfigSettings.KEYCLOAK_REALM,
        }
        response = self.app.put('/v1/users/password', json=data)
        self.assertEqual(response.status_code, 200)
        response_json = json.loads(response.data)
        self.assertEqual(response_json["result"], "success")

        auth_data = {
            "username": "unittestuser",
            "password": "Testing234!",
            "realm": ConfigSettings.KEYCLOAK_REALM,
        }
        response = self.app.post('/v1/users/auth', json=auth_data)
        self.assertEqual(response.status_code, 200)
        response_json = json.loads(response.data)
        self.assertEqual(response_json["error_msg"], "")
        self.assertTrue(response_json["result"]["access_token"])

        # Change the password back so it's consistant for other tests
        data["old_password"] = "Testing234!"
        data["new_password"] = "Testing123!"
        response = self.app.put('/v1/users/password', json=data)
        self.assertEqual(response.status_code, 200)

    @unittest.skip("deprecated the APIs")
    def test_password_missing(self):
        data = {
            "username": "unittestuser",
            "new_password": "Testing234!",
            "realm": ConfigSettings.KEYCLOAK_REALM,
        }
        response = self.app.put('/v1/users/password', json=data)
        self.assertEqual(response.status_code, 400)
        response_json = json.loads(response.data)
        self.assertEqual(response_json["result"], "missing username, old password or new password")

    @unittest.skip("deprecated the APIs")
    def test_password_insecure(self):
        data = {
            "username": "unittestuser",
            "old_password": "Testing123!",
            "new_password": "test",
            "realm": ConfigSettings.KEYCLOAK_REALM,
        }
        response = self.app.put('/v1/users/password', json=data)
        self.assertEqual(response.status_code, 406)
        response_json = json.loads(response.data)
        self.assertEqual(response_json["result"], "invalid new password")

    @unittest.skip("deprecated the APIs")
    # @mock.patch.object(OperationsUser, '__init__', side_effect=Exception())
    def test_password_user_exception(self, mock_data):
        data = {
            "username": "unittestuser",
            "old_password": "Testing123!",
            "new_password": "Testing234!",
            "realm": ConfigSettings.KEYCLOAK_REALM,
        }
        response = self.app.put('/v1/users/password', json=data)
        self.assertEqual(response.status_code, 400)
        response_json = json.loads(response.data)
        self.assertEqual(response_json["result"], "incorrect realm, username or old password: ")

    @unittest.skip("deprecated the APIs")
    # @mock.patch.object(OperationsAdmin, '__init__', side_effect=Exception())
    def test_password_admin_exception(self, mock_data):
        data = {
            "username": "unittestuser",
            "old_password": "Testing123!",
            "new_password": "Testing234!",
            "realm": ConfigSettings.KEYCLOAK_REALM,
        }
        response = self.app.put('/v1/users/password', json=data)
        self.assertEqual(response.status_code, 500)
        response_json = json.loads(response.data)
        self.assertEqual(response_json["result"], 'invalid admin credentials: ')

    @unittest.skip("deprecated the APIs")
    # @mock.patch.object(OperationsAdmin, 'get_user_id', side_effect=Exception())
    def test_password_get_user_exception(self, mock_data):
        data = {
            "username": "unittestuser",
            "old_password": "Testing123!",
            "new_password": "Testing234!",
            "realm": ConfigSettings.KEYCLOAK_REALM,
        }
        response = self.app.put('/v1/users/password', json=data)
        self.assertEqual(response.status_code, 500)
        response_json = json.loads(response.data)
        self.assertEqual(response_json["result"], 'cannot get user id: ')

    def test_user_status(self):
        data = {
            "email": "jiayu.zhang015+10@gmail.com",
        }
        response = self.app.get('/v1/user/status', query_string=data)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json()["email"], "jiayu.zhang015+10@gmail.com")
        self.assertTrue(response.get_json()["status"] in ["active", "disabled", "hibernate"])

    def test_user_status_missing_email(self):
        data = {
        }
        response = self.app.get('/v1/user/status', query_string=data)
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.get_json()["result"], "Missing email")

    def test_user_status_bad_email(self):
        data = {
            "email": "afakeemailthatcertainlydoesnotexist@fake.ca",
        }
        response = self.app.get('/v1/user/status', query_string=data)
        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.get_json()["result"], "User not found")


if __name__ == "__main__":
    unittest.main(warnings='ignore')
