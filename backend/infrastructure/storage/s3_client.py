import uuid

import aiohttp
from aiobotocore.session import get_session
from botocore.exceptions import ClientError


class S3Client:
    def __init__(
        self,
        endpoint_url: str,
        access_key: str,
        secret_key: str,
        bucket: str = "moderation",
    ):
        self.endpoint_url = endpoint_url
        self.access_key = access_key
        self.secret_key = secret_key
        self.bucket = bucket
        self._session = get_session()
        self._bucket_ready = False

    def _generate_key(self, content_type: str) -> str:
        ext = content_type.split("/")[-1]
        return f"images/{uuid.uuid4()}.{ext}"

    def _client(self):
        return self._session.create_client(
            "s3",
            endpoint_url=self.endpoint_url,
            aws_access_key_id=self.access_key,
            aws_secret_access_key=self.secret_key,
        )

    async def _ensure_bucket(self, client) -> None:
        if self._bucket_ready:
            return
        try:
            await client.head_bucket(Bucket=self.bucket)
        except ClientError:
            await client.create_bucket(Bucket=self.bucket)
        self._bucket_ready = True

    async def upload_bytes(
        self,
        data: bytes,
        content_type: str = "image/jpeg",
    ) -> str:
        key = self._generate_key(content_type)
        async with self._client() as client:
            await self._ensure_bucket(client)
            await client.put_object(
                Bucket=self.bucket,
                Key=key,
                Body=data,
                ContentType=content_type,
            )
        return key

    async def upload_from_url(self, url: str) -> str:
        async with aiohttp.ClientSession() as session, session.get(url) as response:
            response.raise_for_status()
            content_type = response.content_type or "image/jpeg"
            data = await response.read()

        return await self.upload_bytes(data, content_type)
