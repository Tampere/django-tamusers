import uuid

import pytest
from allauth.socialaccount.models import EmailAddress, SocialAccount

from tamusers.user_utils import get_or_create_user


class TestGetOrCreateUser:
    @pytest.fixture()
    def payload(self):
        return {
            "sub": uuid.uuid4().hex,
            "email": "tester@gmail.com",
        }

    @pytest.mark.django_db()
    def test_new_user(self, payload):
        user = get_or_create_user(payload, oidc=False)
        assert user.email == "tester@gmail.com"

        account = SocialAccount.objects.get()

        assert account.user == user
        assert account.extra_data == payload
        assert account.provider == "tampere"
        assert account.uid == payload["sub"]

        address = EmailAddress.objects.get()
        assert address.user == user
        assert address.email == "tester@gmail.com"

    @pytest.mark.django_db()
    def test_new_user_no_email(self, payload):
        del payload["email"]
        user = get_or_create_user(payload, oidc=False)
        assert user.email == ""

        account = SocialAccount.objects.get()

        assert account.user == user
        assert account.extra_data == payload
        assert account.provider == "tampere"
        assert account.uid == payload["sub"]

        # No email address created
        assert EmailAddress.objects.count() == 0

    @pytest.mark.django_db()
    def test_existing_user(self, user_model, payload):
        existing_user = user_model.objects.create(
            email="tester@gmail.com", uuid=payload["sub"]
        )

        user = get_or_create_user(payload, oidc=False)

        assert user.uuid.hex == existing_user.uuid
        assert user.email == existing_user.email

        account = SocialAccount.objects.get()

        assert account.user == user
        assert account.extra_data == payload
        assert account.provider == "tampere"
        assert account.uid == payload["sub"]

        address = EmailAddress.objects.get()
        assert address.user == user
        assert address.email == "tester@gmail.com"

    @pytest.mark.django_db()
    def test_existing_social_account(self, user_model, payload):
        existing_user = user_model.objects.create(
            email="tester@gmail.com", uuid=payload["sub"]
        )
        SocialAccount.objects.create(
            user=existing_user,
            extra_data=payload,
            uid=payload["sub"],
            provider="tampere",
        )

        user = get_or_create_user(payload, oidc=False)

        assert user.uuid.hex == existing_user.uuid
        assert user.email == existing_user.email

        account = SocialAccount.objects.get()

        assert account.user == user
        assert account.extra_data == payload
        assert account.provider == "tampere"
        assert account.uid == payload["sub"]

        # No email address created
        assert EmailAddress.objects.count() == 0

    @pytest.mark.django_db()
    def test_existing_email(self, user_model, payload):
        existing_user = user_model.objects.create(
            email="tester@gmail.com", uuid=payload["sub"]
        )

        user = get_or_create_user(payload, oidc=False)

        EmailAddress.objects.create(user=user, email=existing_user.email)

        assert user.uuid.hex == existing_user.uuid
        assert user.email == existing_user.email

        account = SocialAccount.objects.get()

        assert account.user == user
        assert account.extra_data == payload
        assert account.provider == "tampere"
        assert account.uid == payload["sub"]

        address = EmailAddress.objects.get()
        assert address.user == user
        assert address.email == "tester@gmail.com"
