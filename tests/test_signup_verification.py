from verification_service.signup_verification import SignupRequest, prepare_verification


def test_build_context_shapes_link_and_stable_retry_key() -> None:
    request = SignupRequest(
        email="Builder@Example.com",
        verification_token="release-token-123456",
        callback_url="https://console.example.com/verify?source=cli",
        build_id="preview-77",
        commit_sha="abc1234",
        release_channel="preview",
    )

    first = prepare_verification(request)
    retried = prepare_verification(request)

    assert "source=cli&amp;token=release-token-123456" in first.html
    assert "preview-77" in first.subject
    assert first.idempotency_key == retried.idempotency_key
    assert first.idempotency_key.startswith("signup-verification-")
