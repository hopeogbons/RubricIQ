from app.services.auth_service import hash_password, verify_password


def test_hash_then_verify_succeeds():
    hashed = hash_password("hunter2-secret")
    assert hashed != "hunter2-secret"
    assert verify_password("hunter2-secret", hashed) is True


def test_verify_wrong_password_fails():
    hashed = hash_password("hunter2-secret")
    assert verify_password("wrong", hashed) is False


def test_two_hashes_of_same_password_differ():
    assert hash_password("same-input") != hash_password("same-input")
