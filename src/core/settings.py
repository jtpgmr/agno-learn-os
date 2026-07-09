from __future__ import annotations

from pathlib import Path

from pydantic import Field, PostgresDsn, SecretStr, computed_field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class DatabaseSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="DB__",
        extra="ignore",
        case_sensitive=False,
    )

    host: str
    user: str
    password: SecretStr
    database_name: str
    port: int = 5432

    @field_validator("port", mode="before")
    @classmethod
    def setDefaultPort(cls, port: object) -> object:
        return 5432 if port == "" else port

    @computed_field  # type: ignore[prop-decorator]
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
    model_config = SettingsConfigDict(
        env_prefix="AI__",
        extra="ignore",
        case_sensitive=False,
    )

    api_key: SecretStr
    model_provider: str
    provider_base_url: str
    response_model: str = "google/gemini-2.5-flash"
    embedding_model: str = "openai/text-embedding-3-small"

    context_path: str | Path | None = None


class ToolSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="TOOLS__",
        extra="ignore",
        case_sensitive=False,
    )
    # github_access_token: SecretStr | None = None
    github_access_token: SecretStr | None = None
    exa_api_key: SecretStr | None = None


class AppSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_nested_delimiter="__",
        env_ignore_empty=True,
    )

    project_path: str | Path | None = None

    db: DatabaseSettings = Field(default_factory=DatabaseSettings)  # type: ignore[arg-type]
    ai: AIModelSettings = Field(default_factory=AIModelSettings)
    tools: ToolSettings = Field(default_factory=ToolSettings)

    @model_validator(mode="after")
    def applyContextPath(self) -> AppSettings:
        if not self.ai.context_path and self.project_path:
            self.ai.context_path = self.project_path

        return self
