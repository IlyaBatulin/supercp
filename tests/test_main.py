import logging
from collections import defaultdict

import main


def test_successful_access_updates_granted_counter():
    stats = main.new_stats()
    log = logging.getLogger("test")

    result = main.try_access(
        log,
        main.ISSUED_LOGIN,
        main.ISSUED_PASSWORD,
        main.ACCESS_KEY,
        stats,
    )

    assert result is True
    assert stats["granted"] == 1
    assert stats["denied"] == 0


def test_wrong_password_denies_access_and_records_reason():
    stats = main.new_stats()
    log = logging.getLogger("test")

    result = main.try_access(
        log,
        main.ISSUED_LOGIN,
        "wrong-password",
        main.ACCESS_KEY,
        stats,
    )

    assert result is False
    assert stats["granted"] == 0
    assert stats["denied"] == 1
    assert stats["deny_reasons"]["wrong_password"] == 1


def test_wrong_key_denies_access_and_records_reason():
    stats = main.new_stats()
    log = logging.getLogger("test")

    result = main.try_access(
        log,
        main.ISSUED_LOGIN,
        main.ISSUED_PASSWORD,
        "bad-key",
        stats,
    )

    assert result is False
    assert stats["denied"] == 1
    assert stats["deny_reasons"]["wrong_key"] == 1


def test_successful_node_access_updates_node_counter():
    stats = main.new_stats()
    log = logging.getLogger("test")

    result = main.try_node_access(
        log,
        "alpha",
        main.node_password("alpha"),
        stats,
    )

    assert result is True
    assert stats["node_access_granted"]["alpha"] == 1


def test_wrong_node_password_denies_access_and_records_node():
    stats = main.new_stats()
    log = logging.getLogger("test")

    result = main.try_node_access(log, "alpha", "wrong-node-password", stats)

    assert result is False
    assert stats["node_access_denied_reasons"]["wrong_node_password"] == 1
    assert stats["node_access_denied_by_node"]["alpha"] == 1


def test_record_node_selection_works_with_regular_dict_from_session():
    stats = main.new_stats()
    stats["node_selections"] = {}

    main.record_node_selection(stats, "beta")
    main.record_node_selection(stats, "beta")

    assert stats["node_selections"]["beta"] == 2
    assert not isinstance(stats["node_selections"], defaultdict)
