"""Tests for the deduplication invariant: source_type + source_id is the unique identity.

This invariant is declared in CLAUDE.md, .cursor/rules/00-core.mdc and speckit.mdc,
and enforced by UNIQUE(source_type, source_id) in the articles schema.

Import resolves to one of three states:
    not exists                      -> NEW
    exists, same content_hash       -> SKIPPED
    exists, different content_hash  -> UPDATED (version + 1, history recorded)
"""

import pytest

from packages.server.services.import_service import ImportService
from packages.server.storage.models import ArticleCreate, ImportStatus, SourceType


def make_article(
    source_id: str = "page-1",
    content: str = "original content",
    source_type: SourceType = SourceType.NOTION,
    title: str = "Test Article",
    **kwargs,
) -> ArticleCreate:
    """Build an ArticleCreate with sensible defaults."""
    return ArticleCreate(
        source_type=source_type,
        source_id=source_id,
        title=title,
        content=content,
        **kwargs,
    )


class TestContentHash:
    """calculate_content_hash is the basis for change detection."""

    def test_is_deterministic(self):
        assert ImportService.calculate_content_hash("abc") == ImportService.calculate_content_hash(
            "abc"
        )

    def test_differs_for_different_content(self):
        assert ImportService.calculate_content_hash("abc") != ImportService.calculate_content_hash(
            "abd"
        )

    def test_is_md5_hex(self):
        digest = ImportService.calculate_content_hash("abc")
        assert digest == "900150983cd24fb0d6963f7d28e17f72"
        assert len(digest) == 32


class TestThreeStateImport:
    """The core NEW / SKIPPED / UPDATED resolution."""

    async def test_first_import_is_new(self, importer):
        result = await importer.import_article(make_article())

        assert result.status == ImportStatus.NEW
        assert result.article_id is not None

    async def test_reimport_of_identical_content_is_skipped(self, importer):
        first = await importer.import_article(make_article())
        second = await importer.import_article(make_article())

        assert second.status == ImportStatus.SKIPPED
        assert second.article_id == first.article_id, "SKIPPED must point at the existing row"
        assert second.message == "Content unchanged"

    async def test_changed_content_is_updated_in_place(self, importer, db):
        first = await importer.import_article(make_article(content="v1"))
        second = await importer.import_article(make_article(content="v2"))

        assert second.status == ImportStatus.UPDATED
        assert second.article_id == first.article_id, "UPDATED must reuse the same row, not insert"

        rows = await db.fetchall("SELECT id FROM articles")
        assert len(rows) == 1, "an update must not create a second article"

    async def test_skipped_import_does_not_bump_version(self, importer, db):
        await importer.import_article(make_article(content="same"))
        await importer.import_article(make_article(content="same"))

        row = await db.fetchone("SELECT version FROM articles WHERE source_id = ?", ("page-1",))
        assert row["version"] == 1


class TestVersioning:
    """Updates increment version and preserve the previous content."""

    async def test_version_increments_on_each_update(self, importer, db):
        await importer.import_article(make_article(content="v1"))
        await importer.import_article(make_article(content="v2"))
        await importer.import_article(make_article(content="v3"))

        row = await db.fetchone("SELECT version FROM articles WHERE source_id = ?", ("page-1",))
        assert row["version"] == 3

    async def test_update_message_reports_new_version(self, importer):
        await importer.import_article(make_article(content="v1"))
        result = await importer.import_article(make_article(content="v2"))

        assert result.message == "Updated to version 2"

    async def test_update_records_history_with_previous_content(self, importer, db):
        await importer.import_article(make_article(content="v1"))
        await importer.import_article(make_article(content="v2"))

        history = await db.fetchall("SELECT * FROM article_history")
        assert len(history) == 1

        entry = history[0]
        assert entry["old_content"] == "v1"
        assert entry["new_content"] == "v2"
        assert entry["version"] == 1, "history stores the version being superseded"
        assert entry["old_content_hash"] == ImportService.calculate_content_hash("v1")
        assert entry["new_content_hash"] == ImportService.calculate_content_hash("v2")

    async def test_skipped_import_writes_no_history(self, importer, db):
        await importer.import_article(make_article(content="same"))
        await importer.import_article(make_article(content="same"))

        history = await db.fetchall("SELECT * FROM article_history")
        assert history == []

    async def test_current_row_holds_latest_content(self, importer, db):
        await importer.import_article(make_article(content="v1"))
        await importer.import_article(make_article(content="v2"))

        row = await db.fetchone("SELECT content FROM articles WHERE source_id = ?", ("page-1",))
        assert row["content"] == "v2"


class TestIdentityScope:
    """Identity is the (source_type, source_id) pair -- neither field alone."""

    async def test_same_source_id_under_different_source_type_are_distinct(self, importer, db):
        notion = await importer.import_article(
            make_article(source_id="shared-id", source_type=SourceType.NOTION, content="from notion")
        )
        web = await importer.import_article(
            make_article(source_id="shared-id", source_type=SourceType.WEB, content="from web")
        )

        assert notion.status == ImportStatus.NEW
        assert web.status == ImportStatus.NEW, "a different source_type is a different article"
        assert notion.article_id != web.article_id

        rows = await db.fetchall("SELECT id FROM articles")
        assert len(rows) == 2

    async def test_same_source_type_different_source_id_are_distinct(self, importer, db):
        first = await importer.import_article(make_article(source_id="page-1"))
        second = await importer.import_article(make_article(source_id="page-2"))

        assert second.status == ImportStatus.NEW
        assert first.article_id != second.article_id

    async def test_identical_content_under_different_ids_are_not_deduplicated(self, importer, db):
        """content_hash detects change; it is not the identity key."""
        await importer.import_article(make_article(source_id="page-1", content="identical"))
        second = await importer.import_article(make_article(source_id="page-2", content="identical"))

        assert second.status == ImportStatus.NEW, "same content under a new id is still a new article"

        rows = await db.fetchall("SELECT id FROM articles")
        assert len(rows) == 2

    async def test_check_duplicate_is_scoped_by_both_fields(self, importer):
        await importer.import_article(make_article(source_id="page-1", source_type=SourceType.NOTION))

        assert await importer.check_duplicate("notion", "page-1") is not None
        assert await importer.check_duplicate("web", "page-1") is None
        assert await importer.check_duplicate("notion", "page-2") is None


class TestBatchImport:
    """import_batch aggregates per-article results into a summary."""

    async def test_summary_counts_each_state(self, importer):
        await importer.import_article(make_article(source_id="existing", content="unchanged"))
        await importer.import_article(make_article(source_id="to-update", content="v1"))

        result = await importer.import_batch(
            [
                make_article(source_id="brand-new", content="fresh"),
                make_article(source_id="existing", content="unchanged"),
                make_article(source_id="to-update", content="v2"),
            ]
        )

        assert result.summary["new"] == 1
        assert result.summary["updated"] == 1
        assert result.summary["skipped"] == 1
        assert result.summary["error"] == 0

    async def test_batch_is_recorded(self, importer, db):
        result = await importer.import_batch([make_article()], source="cli")

        assert result.batch_id is not None

        batch = await db.fetchone("SELECT * FROM import_batches WHERE id = ?", (result.batch_id,))
        assert batch["source"] == "cli"
        assert batch["new_count"] == 1

    async def test_results_align_with_input_order(self, importer):
        result = await importer.import_batch(
            [make_article(source_id="a"), make_article(source_id="b")]
        )

        assert [item.source_id for item in result.results] == ["a", "b"]


class TestValidation:
    """ArticleCreate rejects malformed input before it reaches the database."""

    @pytest.mark.parametrize(
        "field,value",
        [
            ("source_id", ""),
            ("title", ""),
            ("content", ""),
        ],
    )
    def test_required_fields_reject_empty_string(self, field, value):
        with pytest.raises(ValueError):
            make_article(**{field: value})

    def test_unknown_source_type_is_rejected(self):
        with pytest.raises(ValueError):
            ArticleCreate(
                source_type="linkedin",
                source_id="x",
                title="t",
                content="c",
            )
