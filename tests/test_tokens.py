from ux_fnbase.tokens import DocToken, IndexToken, ScanToken, intersects


def test_doc_intersection():
    assert intersects([DocToken("t", "1")], [DocToken("t", "1")])
    assert not intersects([DocToken("t", "1")], [DocToken("t", "2")])


def test_scan_conservative():
    assert intersects([ScanToken("t")], [DocToken("t", "1")])
    assert intersects([DocToken("t", "1")], [ScanToken("t")])


def test_index_equality():
    assert intersects(
        [IndexToken("t", "status", "done")],
        [IndexToken("t", "status", "done")],
    )
    assert not intersects(
        [IndexToken("t", "status", "done")],
        [IndexToken("t", "status", "backlog")],
    )
