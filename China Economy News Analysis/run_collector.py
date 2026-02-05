#!/usr/bin/env python3
"""Main entry point for news collection and analysis."""

#!/usr/bin/env python3
"""Main entry point for news collection and analysis."""

import argparse
import sys
from pathlib import Path
from datetime import datetime, timedelta
from collections import Counter

sys.path.insert(0, str(Path(__file__).resolve().parent))

from src.database.models import init_db, get_connection
from src.collector.crawler import NewsCrawler


def main():
    parser = argparse.ArgumentParser(description="China Economy News Collector")
    parser.add_argument("--init-db", action="store_true")
    parser.add_argument("--crawl", action="store_true")
    parser.add_argument("--analyze", action="store_true")
    parser.add_argument("--limit", type=int, default=10)
    parser.add_argument("--filter", action="store_true")
    parser.add_argument("--auto", action="store_true")
    args = parser.parse_args()

    if args.init_db or not Path("data/news.db").exists():
        print("Initializing database...")
        init_db()

    if args.auto:
        args.crawl = args.filter = args.analyze = True

    selected_ids = []

    if args.crawl:
        print("Starting news collection...")
        crawler = NewsCrawler()
        results = crawler.crawl_all()
        print(f"\n수집 완료: 총 {results['total']}개, 신규 {results['new']}개")

        conn = get_connection()
        cursor = conn.cursor()

        now = datetime.now()
        cursor.execute(
            "UPDATE news SET published_at = ? WHERE published_at IS NULL",
            (now,)
        )
        conn.commit()

        if args.filter:
            from src.collector.news_filter import filter_news, balance_categories

            print("\n뉴스 필터링 및 선정 중...")
            start_time = now - timedelta(hours=24)

            cursor.execute("""
                SELECT id, original_title, original_content, published_at, source
                FROM news
                WHERE published_at >= ?
                ORDER BY published_at DESC
            """, (start_time,))

            recent_news = [
                {
                    "id": r[0],
                    "original_title": r[1],
                    "original_content": r[2],
                    "published_at": r[3],
                    "source": r[4],
                }
                for r in cursor.fetchall()
            ]

            filtered = filter_news(recent_news)
            selected = balance_categories(filtered, target_count=10)

            if selected:
                selected_ids = [n["id"] for n in selected]

                cursor.execute(
                    "UPDATE news SET expert_review_status='none', is_selected=0"
                )

                for nid in selected_ids:
                    cursor.execute("""
                        UPDATE news
                        SET expert_review_status='queued_today',
                            is_selected=1,
                            analyzed_at=COALESCE(analyzed_at, ?)
                        WHERE id=?
                    """, (now, nid))

                conn.commit()

                print(f"\n✓ {len(selected_ids)}개 뉴스 선정 완료")

        conn.close()

    if args.analyze and selected_ids:
        print("\nAI 분석 시작")
        from src.analyzer.claude_analyzer import ClaudeAnalyzer

        conn = get_connection()
        cursor = conn.cursor()
        analyzer = ClaudeAnalyzer()

        for news_id in selected_ids:
            try:
                cursor.execute(
                    "SELECT original_title FROM news WHERE id=?",
                    (news_id,)
                )
                title = cursor.fetchone()[0]
                analyzer.analyze_news(news_id)
                print(f"✓ 분석 완료: {title[:50]}...")
            except Exception as e:
                print(f"✗ 분석 실패: {e}")

        conn.close()

    if not any([args.init_db, args.crawl, args.analyze, args.auto]):
        parser.print_help()


if __name__ == "__main__":
    main()
