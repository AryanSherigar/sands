from scripts.grant_database_ownership import ownership_statements


def test_each_service_role_is_granted_to_the_admin_before_it_takes_ownership() -> None:
    statements = ownership_statements()

    assert statements == [
        "GRANT core TO postgres",
        "GRANT memory TO postgres",
        "ALTER DATABASE sands_db OWNER TO core",
        "ALTER DATABASE memory_db OWNER TO memory",
    ]
