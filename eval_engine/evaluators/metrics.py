"""
Objective evaluation metrics: ROUGE, BLEU, METEOR, BERTScore, Exact Match,
Token F1, Embedding Cosine Similarity, Distinct-N, Entity Match, etc.

All scores are normalized to [0, 1].
"""
import re
import math
from typing import Optional
from collections import Counter

# ---------------------------------------------------------------------------
# Metric Registry  (consumed by the frontend selector)
# ---------------------------------------------------------------------------

METRIC_REGISTRY = [
    # --- Text similarity ---
    {
        "id": "rouge_1",
        "name": "ROUGE-1",
        "category": "text_similarity",
        "category_label": "文本相似度",
        "needs_reference": True,
        "heavy": False,
        "description": "Unigram overlap between output and reference (recall-oriented)",
    },
    {
        "id": "rouge_2",
        "name": "ROUGE-2",
        "category": "text_similarity",
        "category_label": "文本相似度",
        "needs_reference": True,
        "heavy": False,
        "description": "Bigram overlap between output and reference",
    },
    {
        "id": "rouge_l",
        "name": "ROUGE-L",
        "category": "text_similarity",
        "category_label": "文本相似度",
        "needs_reference": True,
        "heavy": False,
        "description": "Longest common subsequence based F-measure",
    },
    {
        "id": "bleu",
        "name": "BLEU",
        "category": "text_similarity",
        "category_label": "文本相似度",
        "needs_reference": True,
        "heavy": False,
        "description": "Bilingual Evaluation Understudy score (precision-oriented)",
    },
    {
        "id": "meteor",
        "name": "METEOR",
        "category": "text_similarity",
        "category_label": "文本相似度",
        "needs_reference": True,
        "heavy": False,
        "description": "Metric for Evaluation of Translation with Explicit ORdering",
    },
    {
        "id": "exact_match",
        "name": "精确匹配",
        "category": "text_similarity",
        "category_label": "文本相似度",
        "needs_reference": True,
        "heavy": False,
        "description": "Normalized exact match (case/whitespace insensitive)",
    },
    {
        "id": "token_f1",
        "name": "Token F1",
        "category": "text_similarity",
        "category_label": "文本相似度",
        "needs_reference": True,
        "heavy": False,
        "description": "Token-level F1 score between output and reference",
    },
    # --- Semantic similarity ---
    {
        "id": "embedding_cosine",
        "name": "Embedding余弦相似度",
        "category": "semantic_similarity",
        "category_label": "语义相似度",
        "needs_reference": True,
        "heavy": True,
        "description": "Cosine similarity of sentence embeddings (requires model loading)",
    },
    {
        "id": "bertscore_f1",
        "name": "BERTScore F1",
        "category": "semantic_similarity",
        "category_label": "语义相似度",
        "needs_reference": True,
        "heavy": True,
        "description": "Contextual embedding similarity via BERTScore (optional)",
    },
    # --- Generation quality ---
    {
        "id": "distinct_1",
        "name": "Distinct-1 词汇多样性",
        "category": "generation_quality",
        "category_label": "生成质量",
        "needs_reference": False,
        "heavy": False,
        "description": "Ratio of unique unigrams to total unigrams",
    },
    {
        "id": "distinct_2",
        "name": "Distinct-2 词汇多样性",
        "category": "generation_quality",
        "category_label": "生成质量",
        "needs_reference": False,
        "heavy": False,
        "description": "Ratio of unique bigrams to total bigrams",
    },
    {
        "id": "response_length",
        "name": "回复长度",
        "category": "generation_quality",
        "category_label": "生成质量",
        "needs_reference": False,
        "heavy": False,
        "description": "Response length in characters (not normalized, raw count)",
    },
    # --- Factual consistency ---
    {
        "id": "entity_match_f1",
        "name": "实体匹配 F1",
        "category": "factual_consistency",
        "category_label": "事实一致性",
        "needs_reference": True,
        "heavy": False,
        "description": "F1 of named entities (numbers, proper nouns) shared between output and reference",
    },
]

# Quick lookup sets
_ALL_METRIC_IDS = {m["id"] for m in METRIC_REGISTRY}
_LIGHTWEIGHT_IDS = {m["id"] for m in METRIC_REGISTRY if not m["heavy"]}
_NEEDS_REFERENCE = {m["id"] for m in METRIC_REGISTRY if m["needs_reference"]}


class ObjectiveMetricsEvaluator:
    """Compute selected objective metrics for a single (output, reference) pair."""

    def __init__(self, selected_metrics: Optional[list[str]] = None):
        if selected_metrics:
            self._selected = set(selected_metrics) & _ALL_METRIC_IDS
        else:
            # Default: all lightweight metrics
            self._selected = set(_LIGHTWEIGHT_IDS)

        # Lazy-loaded heavy resources (cached across calls)
        self._rouge_scorer = None
        self._embedding_model = None
        self._embedding_tokenizer = None
        self._nltk_ready = False

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def evaluate(self, output_text: str, reference_text: Optional[str] = None) -> dict[str, float]:
        """Return {metric_id: score} for all selected metrics."""
        results: dict[str, float] = {}
        has_ref = bool(reference_text and reference_text.strip())

        for metric_id in self._selected:
            # Skip reference-required metrics when no reference
            if metric_id in _NEEDS_REFERENCE and not has_ref:
                continue
            try:
                fn = getattr(self, f"_compute_{metric_id}", None)
                if fn:
                    val = fn(output_text, reference_text)
                    if val is not None:
                        results[metric_id] = round(val, 4)
            except Exception:
                pass  # silently skip failed metrics

        return results

    # ------------------------------------------------------------------
    # Text similarity metrics
    # ------------------------------------------------------------------

    def _get_rouge_scorer(self):
        if self._rouge_scorer is None:
            from rouge_score import rouge_scorer as rs
            self._rouge_scorer = rs.RougeScorer(["rouge1", "rouge2", "rougeL"], use_stemmer=True)
        return self._rouge_scorer

    def _compute_rouge_1(self, output: str, reference: str) -> float:
        scorer = self._get_rouge_scorer()
        return scorer.score(reference, output)["rouge1"].fmeasure

    def _compute_rouge_2(self, output: str, reference: str) -> float:
        scorer = self._get_rouge_scorer()
        return scorer.score(reference, output)["rouge2"].fmeasure

    def _compute_rouge_l(self, output: str, reference: str) -> float:
        scorer = self._get_rouge_scorer()
        return scorer.score(reference, output)["rougeL"].fmeasure

    def _compute_bleu(self, output: str, reference: str) -> float:
        import sacrebleu
        # sacrebleu expects a list of references
        result = sacrebleu.sentence_bleu(output, [reference])
        return result.score / 100.0  # normalize to 0-1

    def _compute_meteor(self, output: str, reference: str) -> float:
        self._ensure_nltk()
        from nltk.translate.meteor_score import meteor_score as _meteor
        # nltk meteor expects tokenized inputs
        ref_tokens = reference.split()
        out_tokens = output.split()
        if not ref_tokens or not out_tokens:
            return 0.0
        return _meteor([ref_tokens], out_tokens)

    def _compute_exact_match(self, output: str, reference: str) -> float:
        def _normalize(s: str) -> str:
            return re.sub(r"\s+", " ", s.strip().lower())
        return 1.0 if _normalize(output) == _normalize(reference) else 0.0

    def _compute_token_f1(self, output: str, reference: str) -> float:
        pred_tokens = output.lower().split()
        ref_tokens = reference.lower().split()
        if not pred_tokens or not ref_tokens:
            return 0.0
        common = Counter(pred_tokens) & Counter(ref_tokens)
        n_common = sum(common.values())
        if n_common == 0:
            return 0.0
        precision = n_common / len(pred_tokens)
        recall = n_common / len(ref_tokens)
        return 2 * precision * recall / (precision + recall)

    # ------------------------------------------------------------------
    # Semantic similarity metrics
    # ------------------------------------------------------------------

    def _get_embedding_model(self):
        if self._embedding_model is None:
            try:
                from transformers import AutoTokenizer, AutoModel
                import torch
                model_name = "sentence-transformers/all-MiniLM-L6-v2"
                self._embedding_tokenizer = AutoTokenizer.from_pretrained(model_name)
                self._embedding_model = AutoModel.from_pretrained(model_name)
                self._embedding_model.eval()
            except Exception:
                return None, None
        return self._embedding_model, self._embedding_tokenizer

    def _embed(self, text: str):
        import torch
        model, tokenizer = self._get_embedding_model()
        if model is None:
            return None
        inputs = tokenizer(text, return_tensors="pt", truncation=True, max_length=512, padding=True)
        with torch.no_grad():
            outputs = model(**inputs)
        # Mean pooling
        token_embeddings = outputs.last_hidden_state
        attention_mask = inputs["attention_mask"].unsqueeze(-1).expand(token_embeddings.size()).float()
        summed = torch.sum(token_embeddings * attention_mask, dim=1)
        count = torch.clamp(attention_mask.sum(dim=1), min=1e-9)
        return (summed / count).squeeze(0)

    def _compute_embedding_cosine(self, output: str, reference: str) -> Optional[float]:
        import torch
        emb_out = self._embed(output)
        emb_ref = self._embed(reference)
        if emb_out is None or emb_ref is None:
            return None
        cos = torch.nn.functional.cosine_similarity(emb_out.unsqueeze(0), emb_ref.unsqueeze(0))
        # Clamp to [0, 1] (cosine can be negative)
        return max(0.0, float(cos.item()))

    def _compute_bertscore_f1(self, output: str, reference: str) -> Optional[float]:
        try:
            from transformers import AutoTokenizer, AutoModel
            import torch

            model_name = "bert-base-uncased"
            tokenizer = AutoTokenizer.from_pretrained(model_name)
            model = AutoModel.from_pretrained(model_name)
            model.eval()

            def _encode(text):
                inputs = tokenizer(text, return_tensors="pt", truncation=True, max_length=512, padding=True)
                with torch.no_grad():
                    outputs = model(**inputs)
                return outputs.last_hidden_state.squeeze(0)  # (seq_len, hidden)

            ref_emb = _encode(reference)
            out_emb = _encode(output)

            # Cosine similarity matrix
            ref_norm = ref_emb / ref_emb.norm(dim=-1, keepdim=True).clamp(min=1e-9)
            out_norm = out_emb / out_emb.norm(dim=-1, keepdim=True).clamp(min=1e-9)
            sim = torch.mm(out_norm, ref_norm.T)

            precision = sim.max(dim=1).values.mean().item()
            recall = sim.max(dim=0).values.mean().item()
            if precision + recall < 1e-9:
                return 0.0
            f1 = 2 * precision * recall / (precision + recall)
            return max(0.0, min(1.0, f1))
        except Exception:
            return None

    # ------------------------------------------------------------------
    # Generation quality metrics (no reference needed)
    # ------------------------------------------------------------------

    def _compute_distinct_1(self, output: str, _reference: Optional[str] = None) -> float:
        tokens = output.split()
        if not tokens:
            return 0.0
        return len(set(tokens)) / len(tokens)

    def _compute_distinct_2(self, output: str, _reference: Optional[str] = None) -> float:
        tokens = output.split()
        if len(tokens) < 2:
            return 0.0
        bigrams = list(zip(tokens[:-1], tokens[1:]))
        return len(set(bigrams)) / len(bigrams)

    def _compute_response_length(self, output: str, _reference: Optional[str] = None) -> float:
        # Raw character count; NOT normalized to 0-1 (this is informational)
        return float(len(output))

    # ------------------------------------------------------------------
    # Factual consistency metrics
    # ------------------------------------------------------------------

    def _compute_entity_match_f1(self, output: str, reference: str) -> float:
        """F1 of extracted entities (numbers, capitalized words) shared between output and reference."""
        def _extract_entities(text: str) -> set:
            entities = set()
            # Numbers (including decimals)
            entities.update(re.findall(r'\b\d+\.?\d*\b', text))
            # Capitalized words (likely proper nouns) - min 2 chars
            entities.update(w for w in re.findall(r'\b[A-Z][a-zA-Z]{1,}\b', text))
            return entities

        ref_ents = _extract_entities(reference)
        out_ents = _extract_entities(output)
        if not ref_ents and not out_ents:
            return 1.0  # both empty -> perfect match
        if not ref_ents or not out_ents:
            return 0.0
        common = ref_ents & out_ents
        if not common:
            return 0.0
        precision = len(common) / len(out_ents)
        recall = len(common) / len(ref_ents)
        return 2 * precision * recall / (precision + recall)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _ensure_nltk(self):
        if not self._nltk_ready:
            import nltk
            try:
                nltk.data.find("corpora/wordnet")
            except LookupError:
                nltk.download("wordnet", quiet=True)
            try:
                nltk.data.find("corpora/omw-1.4")
            except LookupError:
                nltk.download("omw-1.4", quiet=True)
            self._nltk_ready = True
