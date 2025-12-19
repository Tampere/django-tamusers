import requests

from allauth.socialaccount.providers.oauth2.views import (
    OAuth2Adapter, OAuth2LoginView, OAuth2CallbackView
)
from .provider import TampereOIDCProvider
from tamusers.settings import api_token_auth_settings


class TampereOIDCOAuth2Adapter(OAuth2Adapter):
    provider_id = TampereOIDCProvider.id
    access_token_url = api_token_auth_settings.OIDC_ACCESS_TOKEN_URL
    authorize_url = api_token_auth_settings.OIDC_AUTHORIZE_URL
    profile_url = api_token_auth_settings.OIDC_PROFILE_URL

    def complete_login(self, request, app, token, **kwargs):
        headers = {'Authorization': 'Bearer {0}'.format(token.token)}
        resp = requests.get(self.profile_url, headers=headers)
        assert resp.status_code == 200
        extra_data = resp.json()
        return self.get_provider().sociallogin_from_response(request,
                                                             extra_data)


oauth2_login = OAuth2LoginView.adapter_view(TampereOIDCOAuth2Adapter)
oauth2_callback = OAuth2CallbackView.adapter_view(TampereOIDCOAuth2Adapter)
