from rag_app.text_analysis import analyze_text, index_terms


def test_chinese_query_pipeline_exposes_all_retrieval_stages():
    result = analyze_text("我想知道你现在这个所谓的检索了")

    assert "检索" in result["tokens"]
    assert "检索" in result["filtered_tokens"]
    assert {"我", "你", "现在", "这个", "所谓", "的", "了"}.issubset(set(result["removed_stopwords"]))
    assert result["keywords"]
    assert result["semantic_query"] == "我想知道你现在这个所谓的检索了"
    assert "BGE-M3" in result["semantic_strategy"]


def test_english_stemming_and_entity_detection():
    result = analyze_text("Alice was running APIs in Beijing 2026")

    assert {item["normalized"] for item in result["normalizations"]} >= {"run", "api"}
    assert any(item["text"] == "2026" for item in result["entities"])
    assert "run" in index_terms("running")


def test_compound_project_entity_is_not_mislabeled_as_person():
    result = analyze_text("北斗计划负责人是谁？")

    assert {item["text"]: item["type"] for item in result["entities"]}["北斗计划"] == "项目/计划"
    assert not any(item == {"text": "北斗", "type": "人名"} for item in result["entities"])
