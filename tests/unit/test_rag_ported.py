"""
Unit tests cho các module port từ healthcare-system-backend:
  - normalize_vi
  - important_tokens
  - answer_is_grounded
  - build_not_grounded_reply
  - KeywordRetriever
  - HyDE (mocked)
"""
import pytest

from app.rag.keyword_retriever import KeywordRetriever
from app.rag.relevance import (
    answer_is_grounded,
    build_not_grounded_reply,
    important_tokens,
    normalize_vi,
)


# ─────────────────────────────────────────────
# normalize_vi
# ─────────────────────────────────────────────
class TestNormalizeVi:
    def test_remove_diacritics(self):
        assert normalize_vi("Tiếng Việt") == "tieng viet"

    def test_lowercase(self):
        assert normalize_vi("AMD AI Solutions") == "amd ai solutions"

    def test_remove_special_chars(self):
        assert normalize_vi("giá?! chatbot...") == "gia chatbot"

    def test_d_with_bar(self):
        assert normalize_vi("Điều trị") == "dieu tri"

    def test_empty_string(self):
        assert normalize_vi("") == ""

    def test_numbers_preserved(self):
        result = normalize_vi("Chatbot 2026")
        assert "2026" in result


# ─────────────────────────────────────────────
# important_tokens
# ─────────────────────────────────────────────
class TestImportantTokens:
    def test_filters_stopwords(self):
        tokens = important_tokens("tôi muốn làm chatbot")
        # "tôi" → normalize → "toi" → in stopwords → filtered
        assert "toi" not in tokens
        # "chatbot" và "lam" nên còn
        assert "chatbot" in tokens

    def test_keeps_important_words(self):
        tokens = important_tokens("giá làm chatbot CSKH bao nhiêu")
        assert "chatbot" in tokens or "gia" in tokens

    def test_min_length_2(self):
        tokens = important_tokens("a b c de")
        # single chars should be filtered
        assert "a" not in tokens
        assert "b" not in tokens

    def test_returns_set(self):
        result = important_tokens("chatbot chatbot AI")
        assert isinstance(result, set)


# ─────────────────────────────────────────────
# answer_is_grounded
# ─────────────────────────────────────────────
class TestAnswerIsGrounded:
    def _make_chunk(self, content: str, filename: str = "amd.pdf") -> dict:
        return {"content": content, "metadata": {"filename": filename}}

    def test_grounded_with_matching_chunk(self):
        chunks = [
            self._make_chunk("AMD cung cấp dịch vụ chatbot CSKH cho doanh nghiệp"),
        ]
        assert answer_is_grounded("giá làm chatbot CSKH bao nhiêu", chunks) is True

    def test_not_grounded_with_unrelated_chunks(self):
        chunks = [
            self._make_chunk("Thông tin về máy bay và hàng không"),
            self._make_chunk("Công thức nấu ăn truyền thống"),
        ]
        # query về chatbot, chunks về máy bay → không grounded
        assert answer_is_grounded("giá làm chatbot AI bao nhiêu", chunks) is False

    def test_grounded_returns_true_for_empty_query(self):
        # Query rỗng → cho phép (không block oan)
        assert answer_is_grounded("", []) is True

    def test_grounded_with_multiple_token_overlap(self):
        chunks = [
            self._make_chunk("AMD đã triển khai app mobile AI cho nhiều doanh nghiệp"),
        ]
        assert answer_is_grounded("AMD làm app mobile AI không", chunks) is True

    def test_not_grounded_out_of_domain_query(self):
        chunks = [
            self._make_chunk("AMD cung cấp giải pháp chatbot và automation"),
            self._make_chunk("Dịch vụ AI cho doanh nghiệp Việt Nam"),
        ]
        # Câu hỏi ngoài domain (y tế)
        result = answer_is_grounded("bệnh tiểu đường điều trị thế nào", chunks)
        # Token "tieu duong" không xuất hiện trong chunks → False
        assert result is False


# ─────────────────────────────────────────────
# build_not_grounded_reply
# ─────────────────────────────────────────────
class TestBuildNotGroundedReply:
    def test_contains_redirect_language(self):
        reply = build_not_grounded_reply("bệnh tiểu đường")
        assert "liên hệ" in reply.lower() or "thông tin" in reply.lower()

    def test_includes_contact_when_provided(self):
        reply = build_not_grounded_reply("query", handoff_contact="0901 234 567")
        assert "0901 234 567" in reply

    def test_no_contact_graceful(self):
        reply = build_not_grounded_reply("query")
        assert reply  # không crash, trả về string


# ─────────────────────────────────────────────
# KeywordRetriever
# ─────────────────────────────────────────────
class TestKeywordRetriever:
    def _make_docs(self) -> list[dict]:
        return [
            {"content": "AMD cung cấp dịch vụ chatbot CSKH cho doanh nghiệp Việt Nam", "metadata": {}},
            {"content": "Giá làm app mobile AI phụ thuộc vào tính năng và timeline", "metadata": {}},
            {"content": "Team AMD có kinh nghiệm triển khai automation cho nhà hàng, bán lẻ", "metadata": {}},
            {"content": "Liên hệ AMD qua email hoặc Zalo để được tư vấn miễn phí", "metadata": {}},
            {"content": "Nội dung không liên quan về thời tiết và nông nghiệp", "metadata": {}},
        ]

    def test_returns_relevant_docs(self):
        retriever = KeywordRetriever(self._make_docs(), k=2)
        results = retriever.invoke("chatbot CSKH giá bao nhiêu")
        # Doc đầu tiên về chatbot CSKH phải xuất hiện
        contents = [r["content"] for r in results]
        assert any("chatbot" in c for c in contents)

    def test_returns_k_docs(self):
        retriever = KeywordRetriever(self._make_docs(), k=3)
        results = retriever.invoke("AMD dịch vụ")
        assert len(results) <= 3

    def test_fallback_when_no_overlap(self):
        retriever = KeywordRetriever(self._make_docs(), k=2)
        # Query hoàn toàn vô nghĩa
        results = retriever.invoke("xyzabc 123456")
        # Trả về docs đầu tiên thay vì crash
        assert isinstance(results, list)

    def test_empty_docs(self):
        retriever = KeywordRetriever([], k=4)
        results = retriever.invoke("chatbot")
        assert results == []

    def test_ranks_most_relevant_first(self):
        retriever = KeywordRetriever(self._make_docs(), k=5)
        results = retriever.invoke("app mobile AI")
        # Doc về "app mobile AI" phải đứng đầu
        assert "app mobile" in results[0]["content"]


# ─────────────────────────────────────────────
# HyDE (mock — không tốn OpenAI API)
# ─────────────────────────────────────────────
class TestHyDE:
    @pytest.mark.asyncio
    async def test_returns_query_when_disabled(self):
        from app.rag.hyde import expand_query_hyde

        result = await expand_query_hyde(
            query="giá chatbot bao nhiêu",
            client=None,  # type: ignore
            use_hyde=False,
        )
        assert result == "giá chatbot bao nhiêu"

    @pytest.mark.asyncio
    async def test_fallback_on_client_none(self):
        from app.rag.hyde import expand_query_hyde

        # Khi client=None và use_hyde=True → fallback về query gốc (không crash)
        result = await expand_query_hyde(
            query="giá chatbot bao nhiêu",
            client=None,  # type: ignore
            use_hyde=True,
        )
        assert result == "giá chatbot bao nhiêu"

    @pytest.mark.asyncio
    async def test_mocked_hyde_expansion(self, monkeypatch):
        from app.rag import hyde as hyde_module

        async def mock_create(**kwargs):
            class MockMsg:
                content = "AMD cung cấp dịch vụ chatbot với chi phí linh hoạt từ 20-50 triệu tùy tính năng."
            class MockChoice:
                message = MockMsg()
            class MockResponse:
                choices = [MockChoice()]
            return MockResponse()

        class MockClient:
            class chat:
                class completions:
                    @staticmethod
                    async def create(**kwargs):
                        return await mock_create(**kwargs)

        result = await hyde_module.expand_query_hyde(
            query="giá chatbot bao nhiêu",
            client=MockClient(),  # type: ignore
            use_hyde=True,
        )
        # Phải trả về hypothetical doc, không phải query gốc
        assert len(result) > len("giá chatbot bao nhiêu")
        assert "AMD" in result or "chatbot" in result
