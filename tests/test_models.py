def test_data_files_load(policy_dict, test_cases):
    assert policy_dict["policy_id"] == "PLUM_GHI_2024"
    assert len(test_cases) == 12
