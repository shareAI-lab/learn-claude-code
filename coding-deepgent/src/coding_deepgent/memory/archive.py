from __future__ import annotations

import json
from dataclasses import dataclass
from io import BytesIO
from typing import Protocol

import boto3  # type: ignore[import-untyped]
from botocore.client import Config  # type: ignore[import-untyped]


class MemoryArchiveStore(Protocol):
    def put_json(self, *, object_key: str, payload: dict[str, object]) -> str: ...


@dataclass(frozen=True, slots=True)
class S3ArchiveSettings:
    bucket: str
    endpoint_url: str
    region: str
    access_key_id: str
    secret_access_key: str


class S3MemoryArchiveStore:
    def __init__(self, settings: S3ArchiveSettings) -> None:
        self.settings = settings
        self.client = boto3.client(
            "s3",
            endpoint_url=settings.endpoint_url,
            region_name=settings.region,
            aws_access_key_id=settings.access_key_id,
            aws_secret_access_key=settings.secret_access_key,
            config=Config(
                s3={"addressing_style": "path"},
                proxies={},
            ),
        )

    def put_json(self, *, object_key: str, payload: dict[str, object]) -> str:
        body = json.dumps(payload, ensure_ascii=False, sort_keys=True).encode("utf-8")
        self.client.upload_fileobj(
            BytesIO(body),
            self.settings.bucket,
            object_key,
            ExtraArgs={"ContentType": "application/json"},
        )
        return object_key


class InMemoryArchiveStore:
    def __init__(self) -> None:
        self.objects: dict[str, dict[str, object]] = {}

    def put_json(self, *, object_key: str, payload: dict[str, object]) -> str:
        self.objects[object_key] = dict(payload)
        return object_key
