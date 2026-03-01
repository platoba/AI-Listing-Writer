"""
Keyword Cannibalization Detector – Find when multiple listings from the same
seller target the same keywords, causing internal competition.

Features:
- Extract and normalize keywords from listing titles/descriptions/bullet points
- Detect overlapping keyword targets across listings
- Cannibalization severity scoring
- Consolidation recommendations
- Keyword allocation optimizer
- Export cannibalization report
"""

from __future__ import annotations

import re
import math
from collections import Counter, defaultdict
from dataclasses import dataclass, field, asdict
from typing import Optional


# Common stop words to exclude
STOP_WORDS: set[str] = {
    "a", "an", "the", "and", "or", "but", "in", "on", "at", "to", "for",
    "of", "with", "by", "from", "is", "it", "as", "be", "was", "are",
    "this", "that", "these", "those", "has", "have", "had", "do", "does",
    "did", "will", "would", "could", "should", "may", "might", "can",
    "not", "no", "all", "each", "every", "both", "few", "more", "most",
    "other", "some", "such", "than", "too", "very", "just", "also",
    "about", "up", "out", "so", "if", "into", "over", "after", "before",
    "between", "under", "above", "any", "own", "same", "our", "your",
    "their", "its", "my", "his", "her", "who", "which", "when", "where",
    "how", "what", "why", "been", "being", "were", "new", "used", "one",
    "two", "set", "pack", "pcs", "piece", "pieces",
}


@dataclass
class ListingKeywords:
    """Keywords extracted from a single listing."""
    listing_id: str
    title: str
    keywords: list[str]
    keyword_freq: dict[str, int]
    bigrams: list[str]
    trigrams: list[str]
    primary_keywords: list[str]  # top 5 highest-weight keywords

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class CannibalizationPair:
    """Two listings cannibalizing each other's keywords."""
    listing_a_id: str
    listing_a_title: str
    listing_b_id: str
    listing_b_title: str
    shared_keywords: list[str]
    shared_bigrams: list[str]
    overlap_score: float       # 0-100
    severity: str              # low/medium/high/critical
    recommendation: str

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class KeywordCluster:
    """A cluster of listings targeting the same keyword."""
    keyword: str
    listing_ids: list[str]
    listing_titles: list[str]
    frequency_by_listing: dict[str, int]
    total_frequency: int
    is_cannibalized: bool

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class AllocationSuggestion:
    """Suggest which listing should own which keyword."""
    keyword: str
    assigned_listing_id: str
    assigned_listing_title: str
    reason: str
    competing_listings: list[str]

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class CannibalizationReport:
    """Full cannibalization analysis report."""
    total_listings: int
    total_keywords_analyzed: int
    cannibalized_keywords: int
    cannibalization_pairs: list[CannibalizationPair]
    keyword_clusters: list[KeywordCluster]
    allocation_suggestions: list[AllocationSuggestion]
    overall_score: float       # 0-100, higher = more cannibalization
    risk_level: str
    summary: str

    def to_dict(self) -> dict:
        return {
            "total_listings": self.total_listings,
            "total_keywords_analyzed": self.total_keywords_analyzed,
            "cannibalized_keywords": self.cannibalized_keywords,
            "cannibalization_pairs": [p.to_dict() for p in self.cannibalization_pairs],
            "keyword_clusters": [c.to_dict() for c in self.keyword_clusters],
            "allocation_suggestions": [s.to_dict() for s in self.allocation_suggestions],
            "overall_score": self.overall_score,
            "risk_level": self.risk_level,
            "summary": self.summary,
        }


class KeywordCannibalizationDetector:
    """Detect keyword cannibalization across marketplace listings."""

    def __init__(
        self,
        min_keyword_length: int = 3,
        custom_stop_words: Optional[set[str]] = None,
        ngram_weight: float = 2.0,
    ):
        self.min_keyword_length = min_keyword_length
        self.stop_words = STOP_WORDS | (custom_stop_words or set())
        self.ngram_weight = ngram_weight
        self.listings: dict[str, ListingKeywords] = {}

    def _normalize(self, text: str) -> list[str]:
        """Normalize text to lowercase tokens, remove punctuation & stop words."""
        text = text.lower()
        text = re.sub(r"[^a-z0-9\s-]", " ", text)
        text = re.sub(r"\s+", " ", text).strip()
        tokens = text.split()
        return [
            t for t in tokens
            if len(t) >= self.min_keyword_length and t not in self.stop_words
        ]

    def _extract_ngrams(self, tokens: list[str], n: int) -> list[str]:
        """Extract n-grams from token list."""
        return [" ".join(tokens[i:i + n]) for i in range(len(tokens) - n + 1)]

    def add_listing(
        self,
        listing_id: str,
        title: str,
        description: str = "",
        bullet_points: Optional[list[str]] = None,
        backend_keywords: Optional[list[str]] = None,
    ) -> ListingKeywords:
        """Add a listing and extract its keywords."""
        # Combine all text sources with title weighted heavily
        all_text = f"{title} {title} {title} "  # 3x weight for title
        all_text += f"{description} "
        if bullet_points:
            all_text += " ".join(bullet_points) + " "
        if backend_keywords:
            all_text += " ".join(backend_keywords)

        tokens = self._normalize(all_text)
        freq = Counter(tokens)
        bigrams = self._extract_ngrams(tokens, 2)
        trigrams = self._extract_ngrams(tokens, 3)

        # Primary keywords: top 5 by frequency
        primary = [kw for kw, _ in freq.most_common(5)]

        result = ListingKeywords(
            listing_id=listing_id,
            title=title,
            keywords=list(set(tokens)),
            keyword_freq=dict(freq),
            bigrams=list(set(bigrams)),
            trigrams=list(set(trigrams)),
            primary_keywords=primary,
        )
        self.listings[listing_id] = result
        return result

    def _overlap_score(self, a: ListingKeywords, b: ListingKeywords) -> tuple[float, list[str], list[str]]:
        """Calculate keyword overlap score between two listings."""
        # Unigram overlap
        set_a = set(a.keywords)
        set_b = set(b.keywords)
        shared_kw = set_a & set_b

        if not set_a or not set_b:
            return 0.0, [], []

        # Jaccard-like score for unigrams
        uni_score = len(shared_kw) / len(set_a | set_b) * 100

        # Bigram overlap (weighted higher)
        bg_a = set(a.bigrams)
        bg_b = set(b.bigrams)
        shared_bg = bg_a & bg_b
        bg_score = (
            len(shared_bg) / len(bg_a | bg_b) * 100
            if (bg_a | bg_b)
            else 0
        )

        # Primary keyword overlap (most damaging)
        pri_a = set(a.primary_keywords)
        pri_b = set(b.primary_keywords)
        pri_overlap = len(pri_a & pri_b)
        pri_score = pri_overlap / max(len(pri_a), len(pri_b), 1) * 100

        # Combined score
        combined = (
            uni_score * 0.3
            + bg_score * self.ngram_weight * 0.3
            + pri_score * 0.4
        )
        combined = min(combined, 100)

        return round(combined, 2), sorted(shared_kw), sorted(shared_bg)

    def detect_pairs(
        self, min_overlap: float = 20.0
    ) -> list[CannibalizationPair]:
        """Detect all cannibalization pairs above threshold."""
        pairs: list[CannibalizationPair] = []
        ids = list(self.listings.keys())

        for i in range(len(ids)):
            for j in range(i + 1, len(ids)):
                a = self.listings[ids[i]]
                b = self.listings[ids[j]]
                score, shared_kw, shared_bg = self._overlap_score(a, b)

                if score >= min_overlap:
                    if score >= 70:
                        severity = "critical"
                        rec = ("Consider merging these listings or significantly "
                               "differentiating their keyword strategies")
                    elif score >= 50:
                        severity = "high"
                        rec = ("Differentiate primary keywords — assign distinct "
                               "main keywords to each listing")
                    elif score >= 35:
                        severity = "medium"
                        rec = ("Review shared keywords and allocate primary "
                               "targets to avoid internal competition")
                    else:
                        severity = "low"
                        rec = ("Minor overlap — monitor but no immediate "
                               "action required")

                    pairs.append(CannibalizationPair(
                        listing_a_id=a.listing_id,
                        listing_a_title=a.title,
                        listing_b_id=b.listing_id,
                        listing_b_title=b.title,
                        shared_keywords=shared_kw[:20],
                        shared_bigrams=shared_bg[:10],
                        overlap_score=score,
                        severity=severity,
                        recommendation=rec,
                    ))

        return sorted(pairs, key=lambda p: p.overlap_score, reverse=True)

    def keyword_clusters(self, min_listings: int = 2) -> list[KeywordCluster]:
        """Find keywords shared by multiple listings."""
        kw_map: dict[str, dict[str, int]] = defaultdict(dict)

        for lid, lk in self.listings.items():
            for kw, freq in lk.keyword_freq.items():
                kw_map[kw][lid] = freq

        # Also track bigrams
        for lid, lk in self.listings.items():
            bg_freq = Counter(lk.bigrams)
            for bg, freq in bg_freq.items():
                kw_map[bg][lid] = freq

        clusters: list[KeywordCluster] = []
        for kw, freq_by_listing in kw_map.items():
            if len(freq_by_listing) >= min_listings:
                listing_ids = list(freq_by_listing.keys())
                clusters.append(KeywordCluster(
                    keyword=kw,
                    listing_ids=listing_ids,
                    listing_titles=[
                        self.listings[lid].title for lid in listing_ids
                        if lid in self.listings
                    ],
                    frequency_by_listing=freq_by_listing,
                    total_frequency=sum(freq_by_listing.values()),
                    is_cannibalized=len(freq_by_listing) >= min_listings,
                ))

        return sorted(clusters, key=lambda c: c.total_frequency, reverse=True)

    def suggest_allocation(self) -> list[AllocationSuggestion]:
        """Suggest optimal keyword-to-listing allocation."""
        clusters = self.keyword_clusters(min_listings=2)
        suggestions: list[AllocationSuggestion] = []

        for cluster in clusters[:50]:  # top 50 cannibalized keywords
            # Assign to listing with highest frequency (strongest intent)
            best_listing = max(
                cluster.frequency_by_listing.items(),
                key=lambda x: x[1]
            )
            best_id = best_listing[0]
            best_title = (
                self.listings[best_id].title
                if best_id in self.listings
                else ""
            )

            competitors = [
                lid for lid in cluster.listing_ids if lid != best_id
            ]

            reason = (
                f"Highest frequency ({best_listing[1]}x) in listing text — "
                f"strongest keyword intent for '{cluster.keyword}'"
            )

            suggestions.append(AllocationSuggestion(
                keyword=cluster.keyword,
                assigned_listing_id=best_id,
                assigned_listing_title=best_title,
                reason=reason,
                competing_listings=competitors,
            ))

        return suggestions

    def full_report(self, min_overlap: float = 20.0) -> CannibalizationReport:
        """Generate comprehensive cannibalization report."""
        pairs = self.detect_pairs(min_overlap=min_overlap)
        clusters = self.keyword_clusters(min_listings=2)
        suggestions = self.suggest_allocation()

        total_kw = set()
        for lk in self.listings.values():
            total_kw.update(lk.keywords)

        cannibalized_count = len([c for c in clusters if c.is_cannibalized])

        # Overall score
        if not self.listings:
            overall = 0.0
        else:
            pair_factor = min(len(pairs) * 10, 40)
            severity_factor = sum(
                30 if p.severity == "critical"
                else 20 if p.severity == "high"
                else 10 if p.severity == "medium"
                else 5
                for p in pairs[:5]
            )
            severity_factor = min(severity_factor, 40)
            cannib_ratio = (
                cannibalized_count / len(total_kw) * 100
                if total_kw
                else 0
            )
            cannib_factor = min(cannib_ratio, 20)
            overall = min(pair_factor + severity_factor + cannib_factor, 100)

        overall = round(overall, 1)

        if overall >= 70:
            risk = "critical"
        elif overall >= 50:
            risk = "high"
        elif overall >= 25:
            risk = "medium"
        else:
            risk = "low"

        summary = (
            f"Analyzed {len(self.listings)} listings with {len(total_kw)} unique keywords. "
            f"Found {cannibalized_count} cannibalized keywords across {len(pairs)} listing pairs. "
            f"Risk level: {risk.upper()} ({overall}/100)."
        )

        if pairs:
            worst = pairs[0]
            summary += (
                f" Worst pair: '{worst.listing_a_title[:40]}' vs "
                f"'{worst.listing_b_title[:40]}' ({worst.overlap_score}% overlap)."
            )

        return CannibalizationReport(
            total_listings=len(self.listings),
            total_keywords_analyzed=len(total_kw),
            cannibalized_keywords=cannibalized_count,
            cannibalization_pairs=pairs,
            keyword_clusters=clusters[:30],
            allocation_suggestions=suggestions,
            overall_score=overall,
            risk_level=risk,
            summary=summary,
        )

    def compare_two(
        self, listing_a_id: str, listing_b_id: str
    ) -> Optional[CannibalizationPair]:
        """Compare two specific listings for cannibalization."""
        if listing_a_id not in self.listings or listing_b_id not in self.listings:
            return None

        a = self.listings[listing_a_id]
        b = self.listings[listing_b_id]
        score, shared_kw, shared_bg = self._overlap_score(a, b)

        if score >= 70:
            severity, rec = "critical", "Merge or significantly differentiate"
        elif score >= 50:
            severity, rec = "high", "Assign distinct primary keywords"
        elif score >= 35:
            severity, rec = "medium", "Review and allocate shared keywords"
        else:
            severity, rec = "low", "Minor overlap, monitor only"

        return CannibalizationPair(
            listing_a_id=a.listing_id,
            listing_a_title=a.title,
            listing_b_id=b.listing_id,
            listing_b_title=b.title,
            shared_keywords=shared_kw,
            shared_bigrams=shared_bg,
            overlap_score=score,
            severity=severity,
            recommendation=rec,
        )
