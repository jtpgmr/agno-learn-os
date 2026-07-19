from __future__ import annotations

from uuid import UUID, uuid4

from pydantic import (
    DirectoryPath,
    Field,
    PostgresDsn,
    SecretStr,
    computed_field,
    field_validator,
    model_validator,
)
from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_SETTINGS_CONFIG = SettingsConfigDict(
    extra="ignore",
    case_sensitive=False,
    env_file=".env",
    env_nested_delimiter="__",
    env_ignore_empty=True,
)


class DatabaseSettings(BaseSettings):
    model_config = SettingsConfigDict({**BASE_SETTINGS_CONFIG, "env_prefix": "DB__"})

    host: str
    user: str
    password: SecretStr
    database_name: str
    port: int = 5432

    @field_validator("port", mode="before")
    @classmethod
    def setDefaultPort(cls, port: object) -> object:
        return 5432 if port == "" else port

    @computed_field
    @property
    def dsn(self) -> str:
        return str(
            PostgresDsn.build(
                scheme="postgresql+psycopg",
                username=self.user,
                password=self.password.get_secret_value(),
                host=self.host,
                port=self.port,
                path=self.database_name,
            )
        )


class AIModelSettings(BaseSettings):
    model_config = SettingsConfigDict({**BASE_SETTINGS_CONFIG, "env_prefix": "AI__"})

    api_key: SecretStr
    model_provider: str
    provider_base_url: str
    response_model: str = "google/gemini-2.5-flash"
    embedding_model: str = "openai/text-embedding-3-small"

    session_data_path: DirectoryPath | None = None


class ToolSettings(BaseSettings):
    model_config = SettingsConfigDict({**BASE_SETTINGS_CONFIG, "env_prefix": "TOOLS__"})
    github_access_token: SecretStr | None = None
    exa_api_key: SecretStr | None = None

    @model_validator(mode="after")
    def validateGithubToken(self) -> ToolSettings:
        if self.github_access_token and (
            not (gh_token := self.github_access_token.get_secret_value())
            or not gh_token.startswith("github_pat_")
        ):
            self.github_access_token = None

        return self


class FeatureTestSettings(BaseSettings):
    model_config = SettingsConfigDict({**BASE_SETTINGS_CONFIG, "env_prefix": "FEATURE_TEST__"})

    session_id: str | UUID | None = None

    @model_validator(mode="after")
    def uuidValidator(self) -> FeatureTestSettings:
        if self.session_id:
            self.session_id = str(
                self.session_id if isinstance(self.session_id, UUID) else UUID(self.session_id)
            )
        else:
            self.session_id = str(uuid4())

        return self


class AppSettings(BaseSettings):
    model_config = SettingsConfigDict(**BASE_SETTINGS_CONFIG)

    project_path: DirectoryPath | None = None
    docs_path: DirectoryPath | None = None
    docker_host: str | None = None

    db: DatabaseSettings = Field(default_factory=DatabaseSettings)  # type: ignore[arg-type]
    ai: AIModelSettings = Field(default_factory=AIModelSettings)  # type: ignore[arg-type]
    tools: ToolSettings = Field(default_factory=ToolSettings)
    feature_test: FeatureTestSettings = Field(default_factory=FeatureTestSettings)

    @model_validator(mode="after")
    def applyDocsPath(self) -> AppSettings:
        if not self.docs_path and self.project_path:
            self.docs_path = self.project_path

        return self

    @model_validator(mode="after")
    def applyAIContextPath(self) -> AppSettings:
        if not self.ai.session_data_path and self.project_path:
            self.ai.session_data_path = self.project_path

        return self
