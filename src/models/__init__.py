from pydantic import BaseModel


class S3Settings(BaseModel):
    bucket: str
    key: str
    region: str = "us-east-1"
