from scripts.package_plugin import validate_package

def test_local_plugin_contract_keeps_creator_validation_separate():
    result = validate_package()
    assert result['status'] == 'PASS'
    assert result['creator_validation'] == 'NOT_RUN_CREATOR_UNAVAILABLE'
