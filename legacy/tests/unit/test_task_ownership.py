from karaoke.infra import task_ownership


def test_record_task_owner_sets_with_24h_ttl(mocker):
    fake = mocker.MagicMock()
    mocker.patch("karaoke.infra.task_ownership._redis", return_value=fake)

    task_ownership.record_task_owner("task-1", "user-1")

    fake.setex.assert_called_once_with("task:task-1:user_id", 86400, "user-1")


def test_get_task_owner_returns_stored_value(mocker):
    fake = mocker.MagicMock()
    fake.get.return_value = "user-1"
    mocker.patch("karaoke.infra.task_ownership._redis", return_value=fake)

    assert task_ownership.get_task_owner("task-1") == "user-1"


def test_get_task_owner_missing_returns_none(mocker):
    fake = mocker.MagicMock()
    fake.get.return_value = None
    mocker.patch("karaoke.infra.task_ownership._redis", return_value=fake)

    assert task_ownership.get_task_owner("nope") is None
