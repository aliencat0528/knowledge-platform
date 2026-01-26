#!/usr/bin/env python3
"""
Import AI Chat conversations into Knowledge Platform.

Supports:
- Claude Code (JSONL files from ~/.claude/)
- Cursor (SQLite database)
- Markdown (manually copied content)

Usage:
    python scripts/import_chat.py <path>
    python scripts/import_chat.py <path> --format claude-code
    python scripts/import_chat.py <path> --preview
    python scripts/import_chat.py --clipboard

Examples:
    # Auto-detect and import Claude Code conversations
    python scripts/import_chat.py ~/.claude/projects/my-project/

    # Import specific JSONL file
    python scripts/import_chat.py ~/.claude/projects/my-project/session.jsonl

    # Preview without importing
    python scripts/import_chat.py ~/.claude/projects/ --preview

    # Import from clipboard (markdown)
    python scripts/import_chat.py --clipboard

    # Import markdown file
    python scripts/import_chat.py ~/Desktop/chat.md --format markdown
"""

import argparse
import asyncio
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from packages.server.storage.database import init_db, close_db, get_db
from packages.server.services.chat_import_service import ChatImportService


def get_clipboard_content() -> str:
    """Get content from clipboard."""
    try:
        import subprocess
        result = subprocess.run(
            ["pbpaste"],
            capture_output=True,
            text=True,
            check=True
        )
        return result.stdout
    except (subprocess.CalledProcessError, FileNotFoundError):
        try:
            # Try pyperclip as fallback
            import pyperclip
            return pyperclip.paste()
        except ImportError:
            print("Error: Could not access clipboard. Install pyperclip: pip install pyperclip")
            sys.exit(1)


async def main():
    parser = argparse.ArgumentParser(
        description="Import AI Chat conversations into Knowledge Platform",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s ~/.claude/projects/my-project/
  %(prog)s ~/.claude/projects/my-project/session.jsonl
  %(prog)s ~/.claude/projects/ --preview
  %(prog)s --clipboard
  %(prog)s ~/Desktop/chat.md --format markdown
        """
    )
    parser.add_argument(
        "path",
        type=str,
        nargs="?",
        help="Path to file or directory to import"
    )
    parser.add_argument(
        "--format", "-f",
        choices=["claude-code", "cursor", "markdown", "auto"],
        default="auto",
        help="Source format (default: auto-detect)"
    )
    parser.add_argument(
        "--preview", "-p",
        action="store_true",
        help="Preview contents without importing"
    )
    parser.add_argument(
        "--clipboard", "-c",
        action="store_true",
        help="Import from clipboard (markdown format)"
    )
    parser.add_argument(
        "--title", "-t",
        type=str,
        help="Title for markdown import"
    )

    args = parser.parse_args()

    # Validate arguments
    if not args.path and not args.clipboard:
        parser.print_help()
        print("\nError: Either path or --clipboard is required")
        sys.exit(1)

    print(f"{'=' * 50}")
    print(f"Knowledge Platform - AI Chat Import")
    print(f"{'=' * 50}")

    # Initialize database
    await init_db()
    db = await get_db()

    try:
        service = ChatImportService(db)

        if args.clipboard:
            # Import from clipboard
            print("Reading from clipboard...")
            content = get_clipboard_content()

            if not content.strip():
                print("Error: Clipboard is empty")
                sys.exit(1)

            print(f"Content length: {len(content)} characters")
            print()

            if args.preview:
                print("Preview mode - showing first 500 characters:")
                print("-" * 40)
                print(content[:500])
                if len(content) > 500:
                    print("...")
                print("-" * 40)
            else:
                result = await service.import_markdown(
                    content=content,
                    title=args.title,
                    source="cli-clipboard"
                )
                _print_result(result)

        else:
            # Import from path
            path = Path(args.path).expanduser().resolve()

            if not path.exists():
                print(f"Error: Path not found: {path}")
                sys.exit(1)

            print(f"Path: {path}")
            print(f"Format: {args.format}")
            print()

            if args.preview:
                # Preview mode
                print("Previewing contents...")
                print()

                preview = await service.get_import_preview(path)

                print(f"Detected format: {preview['format']}")
                print(f"Files found: {len(preview['files'])}")
                print(f"Total conversations: {preview['total_conversations']}")

                if preview['files']:
                    print()
                    print("Files:")
                    for f in preview['files'][:5]:
                        print(f"  - {f}")
                    if len(preview['files']) > 5:
                        print(f"  ... and {len(preview['files']) - 5} more")

                if preview['sample_titles']:
                    print()
                    print("Sample titles:")
                    for t in preview['sample_titles'][:5]:
                        print(f"  - {t[:60]}{'...' if len(t) > 60 else ''}")

            else:
                # Import mode
                print("Importing...")
                print()

                if args.format == "claude-code":
                    result = await service.import_claude_code(path, source="cli")
                elif args.format == "cursor":
                    result = await service.import_cursor(path, source="cli")
                elif args.format == "markdown":
                    content = path.read_text(encoding="utf-8")
                    result = await service.import_markdown(
                        content=content,
                        title=args.title or path.stem,
                        source="cli"
                    )
                else:
                    result = await service.auto_import(path, source="cli")

                _print_result(result)

    except FileNotFoundError as e:
        print(f"Error: {e}")
        sys.exit(1)
    except ValueError as e:
        print(f"Error: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    finally:
        await close_db()

    print()
    print(f"{'=' * 50}")
    print("Done!")


def _print_result(result):
    """Print import result."""
    summary = result.summary
    print("Import complete!")
    print("-" * 40)
    print(f"  New:     {summary.get('new', 0)}")
    print(f"  Updated: {summary.get('updated', 0)}")
    print(f"  Skipped: {summary.get('skipped', 0)}")
    print(f"  Errors:  {summary.get('error', 0)}")
    print()

    total = sum(summary.values())
    print(f"Total processed: {total}")

    # Show some results
    if result.results:
        print()
        print("Sample results:")
        for item in result.results[:5]:
            status_icon = {
                "new": "✨",
                "updated": "🔄",
                "skipped": "⏭️",
                "error": "❌",
            }.get(item.status.value, "❓")
            title = item.title[:50] + "..." if len(item.title) > 50 else item.title
            print(f"  {status_icon} {title} ({item.status.value})")

        if len(result.results) > 5:
            print(f"  ... and {len(result.results) - 5} more")


if __name__ == "__main__":
    asyncio.run(main())
