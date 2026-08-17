from __future__ import annotations

import re
from collections.abc import Iterable
from typing import Any

import jieba
import jieba.analyse
import jieba.posseg
from nltk.stem.snowball import SnowballStemmer


jieba.setLogLevel(20)

# 这些词只从 BM25 的词法支路移除。原问题仍会完整交给 BGE-M3，避免破坏语义。
CHINESE_STOP_WORDS = {
    "啊", "吧", "把", "被", "并", "不", "的", "地", "得", "等", "而", "该", "个", "给", "和", "很",
    "或", "及", "即", "几", "将", "就", "了", "吗", "么", "呢", "你", "您", "其", "且", "请", "让",
    "如果", "上", "什么", "是", "所谓", "所", "他", "她", "它", "他们", "她们", "它们", "为什么", "我",
    "我们", "下", "想", "向", "也", "一", "一个", "已经", "以", "以及", "有", "又", "与", "在", "这",
    "这个", "这些", "着", "之", "中", "知道", "现在", "怎么", "怎样",
}
ENGLISH_STOP_WORDS = {
    "a", "an", "and", "are", "as", "at", "be", "been", "but", "by", "can", "could", "did", "do", "does",
    "for", "from", "had", "has", "have", "he", "her", "hers", "him", "his", "how", "i", "if", "in", "into",
    "is", "it", "its", "me", "more", "most", "my", "no", "not", "of", "on", "or", "our", "ours", "please",
    "she", "should", "so", "than", "that", "the", "their", "them", "then", "there", "these", "they", "this",
    "to", "too", "us", "was", "we", "were", "what", "when", "where", "which", "who", "why", "will", "with",
    "would", "you", "your", "yours",
}
STOP_WORDS = CHINESE_STOP_WORDS | ENGLISH_STOP_WORDS
ENTITY_TAGS = {
    "nr": "人名", "nrfg": "人名", "nrt": "人名", "ns": "地名", "nt": "组织", "nz": "专名",
}
COMPOUND_ENTITY_SUFFIXES = {
    "计划": "项目/计划", "项目": "项目/计划", "系统": "产品/系统", "平台": "产品/系统",
    "公司": "组织", "集团": "组织", "大学": "组织", "学院": "组织", "研究院": "组织",
}
TOKEN_RE = re.compile(r"^[\w\u4e00-\u9fff]+$", re.UNICODE)
ENGLISH_RE = re.compile(r"^[A-Za-z]+(?:['-][A-Za-z]+)*$")
EXPLICIT_ENTITY_RE = re.compile(r"[A-Za-z][A-Za-z0-9_.-]{1,}|[A-Z]{2,}|\d{2,}(?:[-/.年]\d+)*")

_stemmer = SnowballStemmer("english")


def _unique(values: Iterable[str]) -> list[str]:
    return list(dict.fromkeys(value for value in values if value))


def tokenize(text: str) -> list[str]:
    """面向检索的中英文分词；保留原文的处理由向量支路负责。"""
    return [token.strip() for token in jieba.lcut(text, cut_all=False) if TOKEN_RE.match(token.strip())]


def _normalize_token(token: str) -> str:
    lowered = token.lower()
    return _stemmer.stem(lowered) if ENGLISH_RE.match(lowered) else lowered


def index_terms(text: str) -> list[str]:
    """生成可持久化的 BM25 词项，保留频次。"""
    return [_normalize_token(token) for token in tokenize(text) if token.lower() not in STOP_WORDS and len(token) > 1]


def analyze_text(text: str) -> dict[str, Any]:
    tokens = tokenize(text)
    removed = _unique(token for token in tokens if token.lower() in STOP_WORDS)
    filtered = [token for token in tokens if token.lower() not in STOP_WORDS and len(token) > 1]

    normalizations = []
    normalized = []
    for token in filtered:
        value = _normalize_token(token)
        normalized.append(value)
        if value != token.lower():
            normalizations.append({"original": token, "normalized": value})

    entities: list[dict[str, str]] = []
    seen_entities: set[str] = set()
    pos_pairs = list(jieba.posseg.cut(text))
    compound_parts: set[str] = set()
    for index, pair in enumerate(pos_pairs):
        entity_type = COMPOUND_ENTITY_SUFFIXES.get(pair.word)
        if entity_type and index > 0:
            prefix = pos_pairs[index - 1].word.strip()
            if 1 < len(prefix) <= 8 and prefix.lower() not in STOP_WORDS and TOKEN_RE.match(prefix):
                value = prefix + pair.word
                entities.append({"text": value, "type": entity_type})
                seen_entities.add(value)
                compound_parts.add(prefix)
    for pair in pos_pairs:
        entity_type = ENTITY_TAGS.get(pair.flag)
        value = pair.word.strip()
        if entity_type and len(value) > 1 and value not in seen_entities and value not in compound_parts:
            entities.append({"text": value, "type": entity_type})
            seen_entities.add(value)
    for value in EXPLICIT_ENTITY_RE.findall(text):
        if value not in seen_entities:
            entities.append({"text": value, "type": "标识/数值"})
            seen_entities.add(value)

    keywords = [
        {"text": word, "weight": round(float(weight), 4)}
        for word, weight in jieba.analyse.extract_tags(text, topK=8, withWeight=True, allowPOS=())
        if word.lower() not in STOP_WORDS and len(word) > 1
    ]
    lexical_terms = normalized + [item["text"].lower() for item in entities] + [item["text"].lower() for item in keywords]
    return {
        "tokens": tokens,
        "filtered_tokens": filtered,
        "removed_stopwords": removed,
        "normalizations": normalizations,
        "entities": entities,
        "keywords": keywords,
        "lexical_terms": lexical_terms,
        "semantic_query": text,
        "semantic_strategy": "保留完整原问题，由 BGE-M3 生成上下文语义向量",
    }
