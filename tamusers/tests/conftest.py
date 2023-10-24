import pytest
from django.contrib.auth import get_user_model


@pytest.fixture()
def user_model():
    return get_user_model()
