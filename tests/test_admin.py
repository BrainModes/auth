import json
import unittest
import warnings
from datetime import datetime
from datetime import timedelta
from unittest import mock

import keycloak
from keycloak import exceptions

from app import create_app
from config import ConfigSettings
from module_keycloak.ops_admin import OperationsAdmin

EXCEPTION_DATA = {
    "response_body": '{ "error": "error" }',
    "error_message": '{ "error": "error" }',
    "response_code": 500,
}


class AdminTests(unittest.TestCase):

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

    def test_create_user(self):
        data = {
            "username": "unittestuser2",
            "password": "Testing123!",
            "email": "unittesting2@test.com",
            "firstname": "Test",
            "lastname": "Test",
            "realm": ConfigSettings.KEYCLOAK_REALM,
        }
        response = self.app.post('/v1/admin/users', json=data)
        self.assertEqual(response.status_code, 200)
        response_json = json.loads(response.data)
        self.assertEqual(response_json["error_msg"], "")
        self.assertEqual(response_json["result"], "User created successfully")

        operations_admin = OperationsAdmin(ConfigSettings.KEYCLOAK_REALM)
        user_id = operations_admin.get_user_id("unittestuser2")
        operations_admin.delete_user(user_id)

    @mock.patch.object(OperationsAdmin, '__init__',
                       side_effect=keycloak.exceptions.KeycloakAuthenticationError(**EXCEPTION_DATA))
    def test_create_user_keycoak_except(self, mock_connect):
        data = {
            "username": "unittestuser2",
            "password": "Testing123!",
            "email": "unittesting2@test.com",
            "firstname": "Test",
            "lastname": "Test",
            "realm": ConfigSettings.KEYCLOAK_REALM,
        }
        response = self.app.post('/v1/admin/users', json=data)
        self.assertEqual(response.status_code, 500)
        response_json = json.loads(response.data)
        self.assertEqual(response_json["result"]["error"], "error")

    @mock.patch.object(OperationsAdmin, '__init__', side_effect=Exception())
    def test_create_user_keycoak_except(self, mock_connect):
        data = {
            "username": "unittestuser2",
            "password": "Testing123!",
            "email": "unittesting2@test.com",
            "firstname": "Test",
            "lastname": "Test",
            "realm": ConfigSettings.KEYCLOAK_REALM,
        }
        response = self.app.post('/v1/admin/users', json=data)
        self.assertEqual(response.status_code, 500)
        response_json = json.loads(response.data)
        self.assertEqual(response_json["result"], "User created failed: ")

    @mock.patch("psycopg2.connect")
    def test_get_username(self, mock_connect):
        query_result = ["testing", "data", datetime.now() + timedelta(1), datetime.now() + timedelta(1)]
        mock_con = mock_connect.return_value
        mock_cur = mock_con.cursor.return_value
        mock_cur.fetchone.return_value = query_result

        data = {
            "username": "unittestuser",
            "invite_code": "testing",
            "realm": ConfigSettings.KEYCLOAK_REALM,
        }
        response = self.app.get('/v1/users/name', query_string=data)
        self.assertEqual(response.status_code, 200)
        response_json = json.loads(response.data)
        self.assertEqual(response_json["error_msg"], "")
        self.assertEqual(response_json["result"]["username"], "unittestuser")

    @mock.patch("psycopg2.connect")
    def test_get_username_not_valid(self, mock_connect):
        query_result = None
        mock_con = mock_connect.return_value
        mock_cur = mock_con.cursor.return_value
        mock_cur.fetchone.return_value = query_result

        data = {
            "username": "unittestuser",
            "invite_code": "testing",
            "realm": ConfigSettings.KEYCLOAK_REALM,
        }
        response = self.app.get('/v1/users/name', query_string=data)
        self.assertEqual(response.status_code, 400)
        response_json = json.loads(response.data)
        self.assertEqual(response_json["result"], "Invitation not valid")

    @mock.patch("psycopg2.connect")
    def test_get_username_expired(self, mock_connect):
        query_result = ["testing", "data", datetime.now() - timedelta(1), datetime.now() + timedelta(1)]
        mock_con = mock_connect.return_value
        mock_cur = mock_con.cursor.return_value
        mock_cur.fetchone.return_value = query_result

        data = {
            "username": "unittestuser",
            "invite_code": "testing",
            "realm": ConfigSettings.KEYCLOAK_REALM,
        }
        response = self.app.get('/v1/users/name', query_string=data)
        self.assertEqual(response.status_code, 400)
        response_json = json.loads(response.data)
        self.assertEqual(response_json["result"], "Invitation expired")

    @mock.patch("psycopg2.connect")
    def test_get_username_missing_info(self, mock_connect):
        query_result = ["testing", "data", datetime.now() + timedelta(1), datetime.now() + timedelta(1)]
        mock_con = mock_connect.return_value
        mock_cur = mock_con.cursor.return_value
        mock_cur.fetchone.return_value = query_result

        data = {
        }
        response = self.app.get('/v1/users/name', query_string=data)
        self.assertEqual(response.status_code, 400)
        response_json = json.loads(response.data)
        self.assertEqual(response_json["result"], "Missing required information")

    @mock.patch.object(OperationsAdmin, '__init__',
                       side_effect=keycloak.exceptions.KeycloakAuthenticationError(**EXCEPTION_DATA))
    @mock.patch("psycopg2.connect")
    def test_get_username_keycloak_except(self, mock_connect, mock_except):
        query_result = ["testing", "data", datetime.now() + timedelta(1), datetime.now() + timedelta(1)]
        mock_con = mock_connect.return_value
        mock_cur = mock_con.cursor.return_value
        mock_cur.fetchone.return_value = query_result

        data = {
            "username": "unittestuser",
            "invite_code": "testing",
            "realm": ConfigSettings.KEYCLOAK_REALM,
        }
        response = self.app.get('/v1/users/name', query_string=data)
        self.assertEqual(response.status_code, 500)
        response_json = json.loads(response.data)
        self.assertEqual(response_json["result"], 'query user by its name failed: 500: { "error": "error" }')

    @mock.patch.object(OperationsAdmin, '__init__',
                       side_effect=keycloak.exceptions.KeycloakAuthenticationError(**EXCEPTION_DATA))
    @mock.patch("psycopg2.connect")
    def test_get_username_except(self, mock_connect, mock_except):
        query_result = ["testing", "data", datetime.now() + timedelta(1), datetime.now() + timedelta(1)]
        mock_con = mock_connect.return_value
        mock_cur = mock_con.cursor.return_value
        mock_cur.fetchone.return_value = query_result

        data = {
            "username": "unittestuser",
            "invite_code": "testing",
            "realm": ConfigSettings.KEYCLOAK_REALM,
        }
        response = self.app.get('/v1/users/name', query_string=data)
        self.assertEqual(response.status_code, 500)
        response_json = json.loads(response.data)
        print(response_json)
        self.assertEqual(response_json["result"], 'query user by its name failed: 500: { "error": "error" }')

    def test_get_email(self):
        data = {
            "email": "unittesting@test.com",
            "realm": ConfigSettings.KEYCLOAK_REALM,
        }
        response = self.app.get('/v1/admin/users/email', query_string=data)
        response_json = json.loads(response.data)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response_json["error_msg"], "")
        self.assertEqual(response_json["result"]["username"], "unittestuser")

    def test_get_email_missing_info(self):
        response = self.app.get('/v1/admin/users/email')
        response_json = json.loads(response.data)
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response_json["result"], "Missing required information")

    def test_get_email_no_user(self):
        data = {
            "email": "unittesting3@test.com",
            "realm": ConfigSettings.KEYCLOAK_REALM,
        }
        response = self.app.get('/v1/admin/users/email', query_string=data)
        response_json = json.loads(response.data)
        self.assertEqual(response.status_code, 404)
        self.assertEqual(response_json["result"], None)

    @mock.patch.object(OperationsAdmin, '__init__',
                       side_effect=keycloak.exceptions.KeycloakAuthenticationError(**EXCEPTION_DATA))
    @mock.patch("psycopg2.connect")
    def test_get_email_keycloak_except(self, mock_connect, mock_except):
        data = {
            "email": "unittesting3@test.com",
            "realm": ConfigSettings.KEYCLOAK_REALM,
        }
        response = self.app.get('/v1/admin/users/email', query_string=data)
        response_json = json.loads(response.data)
        print(response_json)
        self.assertEqual(response_json["result"], 'query user by its email failed: 500: { "error": "error" }')

    @mock.patch.object(OperationsAdmin, '__init__', side_effect=Exception())
    @mock.patch("psycopg2.connect")
    def test_get_email_except(self, mock_connect, mock_except):
        data = {
            "email": "unittesting3@test.com",
            "realm": ConfigSettings.KEYCLOAK_REALM,
        }
        response = self.app.get('/v1/admin/users/email', query_string=data)
        response_json = json.loads(response.data)
        print(response_json)
        self.assertEqual(response_json["result"], 'query user by its email failed: ')
