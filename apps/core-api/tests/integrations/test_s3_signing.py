"""SigV4 against AWS's published signing examples, so the signer is not graded by itself."""

from datetime import datetime, timezone

from app.integrations.s3_signing import (
    SigningCredentials,
    build_authorization,
    sha256_hex,
    sign_request,
)

AWS_EXAMPLE_CREDENTIALS = SigningCredentials(
    access_key_id="AKIAIOSFODNN7EXAMPLE",
    secret_access_key="wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY",
    region="us-east-1",
    service="s3",
)
EMPTY_PAYLOAD_HASH = "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
AWS_EXAMPLE_MOMENT = datetime(2013, 5, 24, tzinfo=timezone.utc)
AWS_GET_OBJECT_SIGNATURE = (
    "f0e8bdb87c964420e857bd35b5d6ed310bd44f0170aba48dd91039c6036bdb41"
)
R2_CREDENTIALS = SigningCredentials("key-id", "secret", "auto", "s3")
R2_HOST = "account.r2.cloudflarestorage.com"


def test_matches_the_aws_get_object_example() -> None:
    headers = {
        "host": "examplebucket.s3.amazonaws.com",
        "range": "bytes=0-9",
        "x-amz-content-sha256": EMPTY_PAYLOAD_HASH,
        "x-amz-date": "20130524T000000Z",
    }

    authorization = build_authorization(
        "GET",
        "/test.txt",
        headers,
        EMPTY_PAYLOAD_HASH,
        AWS_EXAMPLE_MOMENT,
        AWS_EXAMPLE_CREDENTIALS,
    )

    assert authorization == (
        "AWS4-HMAC-SHA256 Credential=AKIAIOSFODNN7EXAMPLE/20130524/us-east-1/s3/"
        "aws4_request, SignedHeaders=host;range;x-amz-content-sha256;x-amz-date, "
        f"Signature={AWS_GET_OBJECT_SIGNATURE}"
    )


def test_sha256_of_nothing_is_the_well_known_empty_hash() -> None:
    assert sha256_hex(b"") == EMPTY_PAYLOAD_HASH


def test_signed_headers_carry_the_payload_hash_and_date() -> None:
    moment = datetime(2026, 10, 26, 12, 30, 5, tzinfo=timezone.utc)

    headers = sign_request(
        "PUT", R2_HOST, "/bucket/a.png", b"data", R2_CREDENTIALS, moment
    )

    assert headers["x-amz-date"] == "20261026T123005Z"
    assert headers["x-amz-content-sha256"] == sha256_hex(b"data")
    assert headers["Authorization"].startswith(
        "AWS4-HMAC-SHA256 Credential=key-id/20261026/auto/s3/aws4_request, "
        "SignedHeaders=host;x-amz-content-sha256;x-amz-date, Signature="
    )


def test_signature_depends_on_the_body_and_the_path() -> None:
    moment = datetime(2026, 10, 26, tzinfo=timezone.utc)

    base = sign_request("PUT", R2_HOST, "/b/a.png", b"one", R2_CREDENTIALS, moment)
    other_body = sign_request(
        "PUT", R2_HOST, "/b/a.png", b"two", R2_CREDENTIALS, moment
    )
    other_path = sign_request(
        "PUT", R2_HOST, "/b/c.png", b"one", R2_CREDENTIALS, moment
    )

    assert base["Authorization"] != other_body["Authorization"]
    assert base["Authorization"] != other_path["Authorization"]


def test_unsafe_characters_in_the_path_are_encoded_before_signing() -> None:
    moment = datetime(2026, 10, 26, tzinfo=timezone.utc)

    spaced = sign_request("PUT", R2_HOST, "/b/a b.png", b"x", R2_CREDENTIALS, moment)
    encoded = sign_request("PUT", R2_HOST, "/b/a%20b.png", b"x", R2_CREDENTIALS, moment)

    assert spaced["Authorization"] != encoded["Authorization"]
