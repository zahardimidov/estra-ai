from core.rate_limit import RateLimiter


class FakeRedis:
    """Mimics the subset of redis.asyncio.Redis used by RateLimiter."""

    def __init__(self):
        self._counters: dict[str, int] = {}
        self.expired: dict[str, int] = {}

    async def incr(self, key: str) -> int:
        self._counters[key] = self._counters.get(key, 0) + 1
        return self._counters[key]

    async def expire(self, key: str, seconds: int) -> None:
        self.expired[key] = seconds


async def test_first_request_within_limit():
    limiter = RateLimiter(FakeRedis())

    allowed = await limiter.check_and_increment("key-1", limit=5)

    assert allowed is True


async def test_requests_within_limit_stay_allowed():
    redis = FakeRedis()
    limiter = RateLimiter(redis)

    results = [await limiter.check_and_increment("key-1", limit=3) for _ in range(3)]

    assert results == [True, True, True]


async def test_request_over_limit_is_rejected():
    redis = FakeRedis()
    limiter = RateLimiter(redis)

    for _ in range(3):
        await limiter.check_and_increment("key-1", limit=3)
    allowed = await limiter.check_and_increment("key-1", limit=3)

    assert allowed is False


async def test_different_identifiers_have_independent_counters():
    redis = FakeRedis()
    limiter = RateLimiter(redis)

    for _ in range(3):
        await limiter.check_and_increment("key-1", limit=3)
    allowed_other = await limiter.check_and_increment("key-2", limit=3)

    assert allowed_other is True


async def test_expire_set_only_on_first_increment():
    redis = FakeRedis()
    limiter = RateLimiter(redis)

    await limiter.check_and_increment("key-1", limit=5)
    await limiter.check_and_increment("key-1", limit=5)

    assert len(redis.expired) == 1
