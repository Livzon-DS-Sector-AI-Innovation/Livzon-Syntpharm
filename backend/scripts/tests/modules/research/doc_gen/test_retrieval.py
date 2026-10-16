"""doc_gen 候选块检索（retrieval.py）单元测试。"""

from __future__ import annotations

from app.modules.research.doc_gen.parsing import TextBlock
from app.modules.research.doc_gen.retrieval import BlockRetriever


def _blocks(*specs: tuple[str, int, str]) -> list[TextBlock]:
    """按 (file_id, index, text) 构造块列表，page 默认 1。"""
    return [TextBlock(file_id=fid, page=1, index=idx, text=text, kind="paragraph") for fid, idx, text in specs]


def test_empty_inputs() -> None:
    assert BlockRetriever([]).candidates(["结晶"]) == []
    retriever = BlockRetriever(_blocks(("f1", 0, "结晶工艺")))
    assert retriever.candidates([]) == []
    assert retriever.candidates(["", "   "]) == []
    assert retriever.candidates(["不存在的词"]) == []


def test_chinese_substring_ranking() -> None:
    blocks = _blocks(
        ("f1", 0, "本章描述结晶工艺的温度控制"),
        ("f1", 1, "本章描述包装工序"),
        ("f1", 2, "收率 收率 收率"),  # 同一关键词重复
        ("f1", 3, "结晶 收率"),  # 两个不同关键词
    )
    retriever = BlockRetriever(blocks)
    result = retriever.candidates(["结晶", "收率"], limit=1, expand_neighbors=0)
    # 不同关键词命中数 2 的块，胜过同一关键词重复 3 次的块
    assert [b.text for b in result] == ["结晶 收率"]

    result2 = retriever.candidates(["包装"], limit=2, expand_neighbors=0)
    assert [b.text for b in result2] == ["本章描述包装工序"]  # 只有它含"包装"


def test_length_normalization() -> None:
    short = "结晶温度控制"
    long = "结晶 " + "无 关 描 述 " * 200
    blocks = _blocks(("f1", 0, long), ("f1", 1, short))
    result = BlockRetriever(blocks).candidates(["结晶"], limit=1, expand_neighbors=0)
    assert [b.text for b in result] == [short]  # 短块得分更高


def test_english_word_boundary_and_case() -> None:
    blocks = _blocks(
        ("f1", 0, "本车间通过 GMP 认证"),  # 大小写无关命中
        ("f1", 1, "apigmp 是接口名"),  # 子串包含但非词边界，不应命中
    )
    result = BlockRetriever(blocks).candidates(["gmp"], expand_neighbors=0)
    assert [b.text for b in result] == ["本车间通过 GMP 认证"]


def test_allow_file_ids_filter() -> None:
    blocks = _blocks(("f1", 0, "结晶工艺"), ("f2", 0, "结晶设备"))
    result = BlockRetriever(blocks).candidates(["结晶"], allow_file_ids=["f2"], expand_neighbors=0)
    assert [b.file_id for b in result] == ["f2"]


def test_roles_filter() -> None:
    blocks = _blocks(("f1", 0, "结晶工艺"), ("f2", 0, "结晶设备"))
    roles = {"f1": ["standard"], "f2": []}  # f2 允许角色集合为空 → 过滤
    result = BlockRetriever(blocks).candidates(["结晶"], roles=roles, expand_neighbors=0)
    assert [b.file_id for b in result] == ["f1"]
    # roles 与 allow_file_ids 同时给出时取交集
    result2 = BlockRetriever(blocks).candidates(["结晶"], roles=roles, allow_file_ids=["f1", "f2"])
    assert [b.file_id for b in result2] == ["f1"]


def test_neighbor_expansion_and_dedup() -> None:
    blocks = _blocks(
        ("f1", 0, "a0"),
        ("f1", 1, "a1"),
        ("f1", 2, "结晶温度"),  # 命中
        ("f1", 3, "a3"),
        ("f1", 4, "a4"),
    )
    result = BlockRetriever(blocks).candidates(["结晶"], expand_neighbors=1)
    assert [b.index for b in result] == [1, 2, 3]  # 邻居扩展且按 index 升序

    # 多命中块共享邻居时去重：index 2 同时是两个命中块的邻居，只出现一次
    blocks2 = _blocks(
        ("f1", 0, "b0"),
        ("f1", 1, "含结晶"),
        ("f1", 2, "b2"),
        ("f1", 3, "含收率"),
    )
    result2 = BlockRetriever(blocks2).candidates(["结晶", "收率"], limit=10, expand_neighbors=1)
    assert [b.index for b in result2] == [0, 1, 2, 3]
    assert len({(b.file_id, b.index) for b in result2}) == len(result2)

    # expand_neighbors=0 时不带邻居
    result3 = BlockRetriever(blocks).candidates(["结晶"], expand_neighbors=0)
    assert [b.index for b in result3] == [2]


def test_limit_and_reading_order() -> None:
    blocks = [
        TextBlock("f1", page=2, index=0, text="结晶 page2", kind="paragraph"),
        TextBlock("f1", page=1, index=1, text="结晶 page1", kind="paragraph"),
        TextBlock("f1", page=3, index=2, text="无关内容", kind="paragraph"),
    ]
    result = BlockRetriever(blocks).candidates(["结晶"], limit=8, expand_neighbors=0)
    # 返回顺序按 (page, index) 升序，便于模型阅读
    assert [(b.page, b.index) for b in result] == [(1, 1), (2, 0)]

    few = BlockRetriever(blocks).candidates(["结晶"], limit=1, expand_neighbors=0)
    assert len(few) == 1


def test_neighbor_not_leaked_across_files() -> None:
    # 邻居扩展仅限同文件同 index 序列，不跨 file_id
    blocks = _blocks(("f1", 0, "结晶"), ("f2", 1, "邻居"), ("f2", 2, "无关"))
    result = BlockRetriever(blocks).candidates(["结晶"], limit=2, expand_neighbors=1)
    assert {b.file_id for b in result} == {"f1"}
