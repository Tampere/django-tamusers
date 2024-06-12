from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils.translation import ugettext as _
from rest_framework import exceptions

try:
    from allauth.socialaccount.models import EmailAddress, SocialAccount

    is_allauth = True
except ImportError:
    is_allauth = False


# TBD: these should be in Django settings
PROVIDER = "tampere"
OIDC_PROVIDER = "tampere_oidc"


def use_social_account():
    return is_allauth and "allauth.socialaccount" in settings.INSTALLED_APPS


def oidc_to_user_data(payload):
    """
    Map OIDC claims to Django user fields.
    """
    payload = payload.copy()

    field_map = {
        "given_name": "first_name",
        "family_name": "last_name",
        "email": "email",
    }
    ret = {}
    for token_attr, user_attr in field_map.items():
        if token_attr not in payload:
            continue
        ret[user_attr] = payload.pop(token_attr)
    ret.update(payload)

    return ret


def populate_user(user, data):
    exclude_fields = ["is_staff", "password", "is_superuser", "id"]
    user_fields = [f.name for f in user._meta.fields if f.name not in exclude_fields]
    changed = False
    for field in user_fields:
        if field in data:
            val = data[field]
            # Only update the email address if it's non-empty
            if not val and field == "email":
                continue
            if getattr(user, field) != val:
                setattr(user, field, val)
                changed = True

    return changed


def update_user(user, payload, oidc=False):
    if oidc:
        payload = oidc_to_user_data(payload)

    changed = populate_user(user, payload)
    if changed or not user.pk:
        user.save()

    ad_groups = payload.get("ad_groups", None)
    # Only update AD groups if it's a list of non-empty strings
    if isinstance(ad_groups, list) and (
        all([isinstance(x, str) and x for x in ad_groups])
    ):
        user.update_ad_groups(ad_groups)


@transaction.atomic()
def get_or_create_user(payload, oidc=False):
    user_id = payload.get("sub")
    if not user_id:
        msg = _("Invalid payload.")
        raise exceptions.AuthenticationFailed(msg)

    user_model = get_user_model()

    try:
        user = user_model.objects.select_for_update().get(uuid=user_id)
    except user_model.DoesNotExist:
        user = user_model(uuid=user_id)
        user.set_unusable_password()

    update_user(user, payload, oidc)
    create_social_account(user, user_id, payload, oidc)

    return user


def create_social_account(user, user_id, payload, oidc):
    """Creates SocialAccount instance for this user if one
    does not exist already.

    Raises AuthenticationFailed if existing SocialAccount matching provider
    and UUID for another user.

    If user does not have an existing SocialAccount, will also attempt to create or match an
    EmailAddress instance.
    """
    if not use_social_account():
        return None

    provider_name = OIDC_PROVIDER if oidc else PROVIDER
    kwargs = {"provider": provider_name, "uid": user_id}

    try:
        account = SocialAccount.objects.get(**kwargs)

        if account.user_id != user.pk:
            msg = _("User already exists for this account.")
            raise exceptions.AuthenticationFailed(msg)

    except SocialAccount.DoesNotExist:
        account = SocialAccount.objects.create(
            **kwargs,
            user=user,
            extra_data=payload,
        )
        create_email_address(user)

    return account


def create_email_address(user):
    """Creates EmailAddress instance for this user if no address
    can be found.


    Returns None if user does not have an email address, or if the email address matching
    that of the user already exists for another user.
    """
    if not use_social_account():
        return None

    email = (user.email or "").strip().lower()

    if not email:
        return None

    try:
        # ensure this email address does not already exist
        address = EmailAddress.objects.get(email__iexact=email)

        if address.user_id != user.pk:
            return None

    except EmailAddress.DoesNotExist:
        address = EmailAddress.objects.create(
            user=user,
            email=email,
            primary=True,
            verified=True,
        )

    return address
