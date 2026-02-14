"""Unit tests for JWT authentication module."""

import pytest
import sys
from pathlib import Path
from datetime import timedelta

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from auth.jwt import encode_token, decode_token, TokenData, UserRole, SECRET_KEY


class TestEncodeToken:
    def test_encode_returns_string(self):
        token = encode_token(user_id="u1", username="alice")
        assert isinstance(token, str)
        assert len(token) > 0

    def test_encode_with_role(self):
        token = encode_token(user_id="u1", username="alice", role=UserRole.ADMIN)
        data = decode_token(token)
        assert data is not None
        assert data.role == UserRole.ADMIN

    def test_encode_with_custom_expiry(self):
        token = encode_token(
            user_id="u1", username="alice",
            expires_delta=timedelta(minutes=5),
        )
        data = decode_token(token)
        assert data is not None


class TestDecodeToken:
    def test_decode_valid_token(self):
        token = encode_token(user_id="u1", username="bob")
        data = decode_token(token)
        assert data is not None
        assert data.user_id == "u1"
        assert data.username == "bob"
        assert data.role == UserRole.USER

    def test_decode_invalid_token(self):
        result = decode_token("invalid.token.string")
        assert result is None

    def test_decode_empty_string(self):
        result = decode_token("")
        assert result is None

    def test_decode_tampered_token(self):
        token = encode_token(user_id="u1", username="alice")
        # Flip a character in the payload
        tampered = token[:-5] + "XXXXX"
        result = decode_token(tampered)
        assert result is None

    def test_decode_expired_token(self):
        token = encode_token(
            user_id="u1", username="alice",
            expires_delta=timedelta(seconds=-1),
        )
        result = decode_token(token)
        assert result is None


class TestTokenData:
    def test_token_data_defaults(self):
        td = TokenData(user_id="u1", username="alice")
        assert td.role == UserRole.USER
        assert td.exp is None

    def test_token_data_roundtrip(self):
        token = encode_token(user_id="uid-42", username="charlie", role=UserRole.ADMIN)
        td = decode_token(token)
        assert td is not None
        assert td.user_id == "uid-42"
        assert td.username == "charlie"
        assert td.role == UserRole.ADMIN
        assert td.exp is not None
