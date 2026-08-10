"""Unit tests for Phase 2 authentication connectors with API mocking."""
import json
import pytest
from unittest.mock import patch, MagicMock

from connectors.youtube import YouTubeConnector
from connectors.facebook import FacebookConnector
from connectors.instagram import InstagramConnector


def test_youtube_auth_from_file(tmp_path):
    token_file = tmp_path / "youtube_token.json"
    dummy_data = {
        "token": "fake_yt_access_token",
        "refresh_token": "fake_yt_refresh_token",
        "token_uri": "https://oauth2.googleapis.com/token",
        "client_id": "fake_client_id",
        "client_secret": "fake_client_secret",
        "scopes": ["https://www.googleapis.com/auth/youtube.upload"],
    }
    token_file.write_text(json.dumps(dummy_data))

    yt = YouTubeConnector(token_path=str(token_file))

    with patch("connectors.youtube.auth.Credentials") as mock_creds_cls:
        mock_creds = MagicMock()
        mock_creds.expired = False
        mock_creds.valid = True
        mock_creds_cls.from_authorized_user_file.return_value = mock_creds

        authenticated = yt.authenticate()

        assert authenticated is True


def test_facebook_auth_from_pages_config(tmp_path):
    pages_file = tmp_path / "facebook_pages.json"
    dummy_pages = {
        "pages": {
            "Yen Handmade Leather": {
                "page_id": "123456789",
                "access_token": "fake_fb_page_access_token",
                "expires_at": "2099-12-31T23:59:59Z",
            }
        }
    }
    pages_file.write_text(json.dumps(dummy_pages))

    fb = FacebookConnector(brand_name="Yen Handmade Leather")

    with patch("core.account_manager.FB_PAGES_FILE", pages_file), patch("requests.get") as mock_get:
        fb.load_brand_credentials("Yen Handmade Leather")
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"id": "123456789", "name": "Yen Handmade Leather Page"}
        mock_get.return_value = mock_response

        authenticated = fb.authenticate()

        assert authenticated is True
        assert fb.access_token == "fake_fb_page_access_token"
        assert fb.page_id == "123456789"


def test_instagram_auth_from_file_and_validation(tmp_path):
    token_file = tmp_path / "instagram_token.json"
    dummy_data = {
        "instagram_account_id": "987654321",
        "access_token": "fake_ig_access_token",
    }
    token_file.write_text(json.dumps(dummy_data))

    ig = InstagramConnector(token_path=str(token_file))

    with patch("requests.get") as mock_get:
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"id": "987654321", "username": "test_business_account"}
        mock_get.return_value = mock_response

        authenticated = ig.authenticate()

        assert authenticated is True
        assert ig.instagram_account_id == "987654321"
        assert ig.access_token == "fake_ig_access_token"
