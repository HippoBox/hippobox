from enum import StrEnum

from pydantic import BaseModel, Field


class OAuthProvider(StrEnum):
    GOOGLE = "google"
    GITHUB = "github"


class OAuthProviderConfig(BaseModel):
    provider: OAuthProvider
    client_id: str
    client_secret: str
    authorize_url: str
    token_url: str
    userinfo_url: str


class OAuthProviderPublicConfig(BaseModel):
    provider: OAuthProvider
    start_path: str = Field(description="Backend endpoint path to start OAuth login.")


class OAuthIdentityProfile(BaseModel):
    provider: OAuthProvider
    provider_user_id: str
    email: str
    name: str
    email_verified: bool = False


class OAuthProvidersResponse(BaseModel):
    providers: list[OAuthProviderPublicConfig]
