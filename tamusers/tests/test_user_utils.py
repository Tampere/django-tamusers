import uuid

import pytest
from allauth.socialaccount.models import EmailAddress, SocialAccount
from django.test import override_settings
from rest_framework import exceptions

from tamusers.user_utils import get_or_create_user


class TestGetOrCreateUser:
    @pytest.fixture()
    def payload(self):
        return {
            "sub": uuid.uuid4().hex,
            "email": "tester@gmail.com",
        }

    @pytest.mark.django_db(transaction=True)
    def test_new_user_payload_missing_sub(self, user_model):
        with pytest.raises(exceptions.AuthenticationFailed):
            get_or_create_user({}, oidc=False)

        assert user_model.objects.count() == 0

    @pytest.mark.django_db(transaction=True)
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

    @pytest.mark.django_db(transaction=True)
    def test_new_user_not_using_social_account(self, payload, settings):
        installed_apps = settings.INSTALLED_APPS[::]
        installed_apps.remove("allauth.socialaccount")

        with override_settings(INSTALLED_APPS=installed_apps):
            user = get_or_create_user(payload, oidc=False)
            assert user.email == "tester@gmail.com"

        assert SocialAccount.objects.count() == 0
        assert EmailAddress.objects.count() == 0

    @pytest.mark.django_db(transaction=True)
    def test_new_user_oidc(self, payload):
        user = get_or_create_user(payload, oidc=True)
        assert user.email == "tester@gmail.com"

        account = SocialAccount.objects.get()

        assert account.user == user
        assert account.extra_data == payload
        assert account.provider == "tampere_oidc"
        assert account.uid == payload["sub"]

        address = EmailAddress.objects.get()
        assert address.user == user
        assert address.email == "tester@gmail.com"

    @pytest.mark.django_db(transaction=True)
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

    @pytest.mark.django_db(transaction=True)
    def test_new_user_no_email_existing_empty_email(self, user_model, payload):
        del payload["email"]

        address = EmailAddress.objects.create(
            user=user_model.objects.create_user(username="tester"), email=""
        )

        user = get_or_create_user(payload, oidc=False)
        assert user.email == ""

        account = SocialAccount.objects.get()

        assert account.user == user
        assert account.extra_data == payload
        assert account.provider == "tampere"
        assert account.uid == payload["sub"]

        # No email address created
        assert EmailAddress.objects.count() == 1
        assert EmailAddress.objects.first().user == address.user

    @pytest.mark.django_db(transaction=True)
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

    @pytest.mark.django_db(transaction=True)
    def test_existing_user_empty_email(self, user_model, payload):
        del payload["email"]

        existing_user = user_model.objects.create(email="", uuid=payload["sub"])

        user = get_or_create_user(payload, oidc=False)

        assert user.uuid.hex == existing_user.uuid
        assert user.email == existing_user.email

        account = SocialAccount.objects.get()

        assert account.user == user
        assert account.extra_data == payload
        assert account.provider == "tampere"
        assert account.uid == payload["sub"]

        assert EmailAddress.objects.count() == 0

    @pytest.mark.django_db(transaction=True)
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

    @pytest.mark.django_db(transaction=True)
    def test_existing_email(self, user_model, payload):
        existing_user = user_model.objects.create(
            email="tester@gmail.com", uuid=payload["sub"]
        )

        EmailAddress.objects.create(user=existing_user, email=existing_user.email)

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

    @pytest.mark.django_db(transaction=True)
    def test_existing_email_for_other_user(self, user_model, payload):
        existing_user = user_model.objects.create(
            email="tester-2@gmail.com", uuid=uuid.uuid4().hex
        )

        EmailAddress.objects.create(user=existing_user, email="tester@gmail.com")

        get_or_create_user(payload, oidc=False)

        assert user_model.objects.count() == 2
        assert SocialAccount.objects.count() == 1
        assert EmailAddress.objects.count() == 1

        assert EmailAddress.objects.first().user == existing_user

    @pytest.mark.django_db(transaction=True)
    def test_existing_social_account_for_other_user(self, user_model, payload):
        existing_user = user_model.objects.create(
            email="tester-2@gmail.com", uuid=uuid.uuid4().hex
        )

        SocialAccount.objects.create(
            user=existing_user,
            uid=payload["sub"],
            provider="tampere",
        )

        with pytest.raises(exceptions.AuthenticationFailed):
            get_or_create_user(payload, oidc=False)

        assert user_model.objects.count() == 1
        assert SocialAccount.objects.count() == 1
        assert EmailAddress.objects.count() == 0
