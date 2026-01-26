import requests

from allauth.socialaccount.providers.oauth2.views import (OAuth2Adapter,
                                                          OAuth2LoginView,
                                                          OAuth2CallbackView)
from .provider import TampereProvider
from tamusers.settings import api_token_auth_settings


class TampereOAuth2Adapter(OAuth2Adapter):
    provider_id = TampereProvider.id
    access_token_url = api_token_auth_settings.OAUTH2_ACCESS_TOKEN_URL
    authorize_url = api_token_auth_settings.OAUTH2_AUTHORIZE_URL
    profile_url = api_token_auth_settings.OAUTH2_PROFILE_URL

    def complete_login(self, request, app, token, **kwargs):
        headers = {'Authorization': 'Bearer {0}'.format(token.token)}
        resp = requests.get(self.profile_url, headers=headers)
        extra_data = resp.json()
        return self.get_provider().sociallogin_from_response(request,
                                                             extra_data)


oauth2_login = OAuth2LoginView.adapter_view(TampereOAuth2Adapter)
oauth2_callback = OAuth2CallbackView.adapter_view(TampereOAuth2Adapter)
