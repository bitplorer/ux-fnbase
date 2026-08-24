from ux_fnbase.ids import new_id


def test_id_length_and_unique():
    ids = {new_id() for _ in range(200)}
    assert len(ids) == 200
    assert all(len(i) == 26 for i in ids)
