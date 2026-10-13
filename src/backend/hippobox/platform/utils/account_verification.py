"""Atomic, user-bound email challenges stored as keyed hashes, never plaintext."""

import hashlib
import hmac
import json
import secrets
from typing import Literal

from redis.exceptions import WatchError

from hippobox.platform.core.cache.redis import RedisManager
from hippobox.platform.core.config.settings import SETTINGS

ChallengePurpose = Literal["account_delete", "password_change"]


def _digest(
    user_id: int, nonce: str, code: str, purpose: ChallengePurpose = "account_delete"
) -> str:
    domain = purpose.replace("_", "-")
    return hmac.new(
        SETTINGS.SECRET_KEY.encode(),
        f"{domain}:{user_id}:{nonce}:{code}".encode(),
        hashlib.sha256,
    ).hexdigest()


async def issue_email_code(
    user_id: int,
    *,
    ttl: int,
    cooldown: int,
    request_limit: int,
    request_window: int,
    attempt_limit: int = 5,
    purpose: ChallengePurpose = "account_delete",
) -> tuple[str | None, int]:
    redis = await RedisManager.get_client()
    prefix = f"{purpose}:{user_id}"
    challenge, throttle, budget = (
        f"{prefix}:{part}" for part in ("challenge", "cooldown", "budget")
    )
    failures = f"{prefix}:failures"
    for _ in range(8):
        async with redis.pipeline(transaction=True) as pipe:
            try:
                await pipe.watch(challenge, throttle, budget, failures)
                if int(await pipe.get(failures) or 0) >= attempt_limit:
                    return None, max(1, await pipe.ttl(failures))
                remaining = await pipe.ttl(throttle)
                if remaining > 0:
                    return None, remaining
                requests = int(await pipe.get(budget) or 0)
                budget_ttl = await pipe.ttl(budget)
                if requests >= request_limit:
                    return None, max(1, budget_ttl)
                code = f"{secrets.randbelow(1_000_000):06d}"
                nonce = secrets.token_hex(16)
                payload = json.dumps(
                    {"nonce": nonce, "digest": _digest(user_id, nonce, code, purpose)}
                )
                pipe.multi()
                pipe.set(challenge, payload, ex=ttl)
                pipe.set(throttle, "1", ex=cooldown)
                pipe.set(budget, requests + 1, ex=budget_ttl if budget_ttl > 0 else request_window)
                await pipe.execute()
                return code, cooldown
            except WatchError:
                continue
    raise RuntimeError("Email challenge contention")


async def consume_email_code(
    user_id: int,
    code: str,
    *,
    attempt_limit: int,
    window: int,
    consume: bool = True,
    purpose: ChallengePurpose = "account_delete",
) -> bool:
    redis = await RedisManager.get_client()
    prefix = f"{purpose}:{user_id}"
    challenge, failures = f"{prefix}:challenge", f"{prefix}:failures"
    for _ in range(8):
        async with redis.pipeline(transaction=True) as pipe:
            try:
                await pipe.watch(challenge, failures)
                raw = await pipe.get(challenge)
                attempts = int(await pipe.get(failures) or 0)
                if attempts >= attempt_limit:
                    return False
                stored = json.loads(raw) if raw else None
                valid = stored is not None and hmac.compare_digest(
                    stored["digest"], _digest(user_id, stored["nonce"], code, purpose)
                )
                failure_ttl = await pipe.ttl(failures)
                pipe.multi()
                if valid:
                    if consume:
                        pipe.delete(challenge)
                    else:
                        # Keep WATCH/MULTI active for verification without consuming or extending TTL.
                        pipe.get(challenge)
                else:
                    pipe.set(failures, attempts + 1, ex=failure_ttl if failure_ttl > 0 else window)
                    if attempts + 1 >= attempt_limit:
                        pipe.delete(challenge)
                await pipe.execute()
                return valid
            except WatchError:
                continue
    raise RuntimeError("Email challenge contention")


# Preserve the existing deletion callers and default challenge namespace.
issue_deletion_code = issue_email_code
consume_deletion_code = consume_email_code
