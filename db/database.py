# coding=utf-8
"""
数据库操作模块

提供新闻数据的数据库读写功能，只实现 news_items 表的逻辑
"""

import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from .models import NewsItem, NewsData
from .utils import normalize_url


class NewsDatabase:
    """新闻数据库操作类"""

    # news_items 表的 SQL 定义
    NEWS_ITEMS_SCHEMA = """
    -- 新闻条目表
    -- 以 URL + platform_id 为唯一标识，支持去重存储
    CREATE TABLE IF NOT EXISTS news_items (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT NOT NULL,
        platform_id TEXT NOT NULL,
        rank INTEGER NOT NULL,
        url TEXT DEFAULT '',
        mobile_url TEXT DEFAULT '',
        first_crawl_time TEXT NOT NULL,      -- 首次抓取时间
        last_crawl_time TEXT NOT NULL,       -- 最后抓取时间
        crawl_count INTEGER DEFAULT 1,       -- 抓取次数
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );

    -- 索引定义
    CREATE INDEX IF NOT EXISTS idx_news_platform ON news_items(platform_id);
    CREATE INDEX IF NOT EXISTS idx_news_crawl_time ON news_items(last_crawl_time);
    CREATE INDEX IF NOT EXISTS idx_news_title ON news_items(title);
    
    -- URL + platform_id 唯一索引（仅对非空 URL，实现去重）
    CREATE UNIQUE INDEX IF NOT EXISTS idx_news_url_platform
        ON news_items(url, platform_id) WHERE url != '';
    """

    def __init__(
        self,
        db_path: str = "newsradar.db",
        timezone: str = "Asia/Shanghai",
    ):
        """
        初始化数据库

        Args:
            db_path: 数据库文件路径（可以是相对路径或绝对路径）
            timezone: 时区配置（默认 Asia/Shanghai）
        """
        self.db_path = Path(db_path)
        self.timezone = timezone
        
        # 确保数据库文件所在目录存在
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        
        # 初始化数据库表
        self._init_database()

    def _get_connection(self) -> sqlite3.Connection:
        """获取数据库连接"""
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row  # 使用 Row 工厂，方便访问列
        return conn

    def _init_database(self):
        """初始化数据库表结构"""
        conn = self._get_connection()
        try:
            conn.executescript(self.NEWS_ITEMS_SCHEMA)
            conn.commit()
        finally:
            conn.close()

    def _get_current_time(self) -> datetime:
        """获取当前时间（使用配置的时区）"""
        # 简化实现：直接使用本地时间
        # 如果需要真正的时区支持，可以使用 pytz 或 zoneinfo
        return datetime.now()

    def save_news_data(self, data: NewsData) -> Tuple[bool, int, int]:
        """
        保存新闻数据到数据库

        Args:
            data: NewsData 对象

        Returns:
            (success, new_count, updated_count) 元组
        """
        try:
            conn = self._get_connection()
            cursor = conn.cursor()

            # 获取当前时间戳
            now_str = self._get_current_time().strftime("%Y-%m-%d %H:%M:%S")

            # 统计计数器
            new_count = 0
            updated_count = 0

            # 遍历所有平台的新闻条目
            for platform_id, news_list in data.items.items():
                for item in news_list:
                    try:
                        # 标准化 URL（去除动态参数）
                        normalized_url = normalize_url(item.url, platform_id) if item.url else ""

                        # 检查是否已存在（通过标准化 URL + platform_id）
                        if normalized_url:
                            cursor.execute("""
                                SELECT id, title FROM news_items
                                WHERE url = ? AND platform_id = ?
                            """, (normalized_url, platform_id))
                            existing = cursor.fetchone()

                            if existing:
                                # 已存在，更新记录
                                existing_id, existing_title = existing

                                # 更新现有记录
                                cursor.execute("""
                                    UPDATE news_items SET
                                        title = ?,
                                        rank = ?,
                                        mobile_url = ?,
                                        last_crawl_time = ?,
                                        crawl_count = crawl_count + 1,
                                        updated_at = ?
                                    WHERE id = ?
                                """, (
                                    item.title,
                                    item.rank,
                                    item.mobile_url,
                                    data.crawl_time,
                                    now_str,
                                    existing_id
                                ))
                                updated_count += 1
                            else:
                                # 不存在，插入新记录（存储标准化后的 URL）
                                cursor.execute("""
                                    INSERT INTO news_items
                                    (title, platform_id, rank, url, mobile_url,
                                     first_crawl_time, last_crawl_time, crawl_count,
                                     created_at, updated_at)
                                    VALUES (?, ?, ?, ?, ?, ?, ?, 1, ?, ?)
                                """, (
                                    item.title,
                                    platform_id,
                                    item.rank,
                                    normalized_url,
                                    item.mobile_url,
                                    data.crawl_time,
                                    data.crawl_time,
                                    now_str,
                                    now_str
                                ))
                                new_count += 1
                        else:
                            # URL 为空的情况，直接插入（不做去重）
                            cursor.execute("""
                                INSERT INTO news_items
                                (title, platform_id, rank, url, mobile_url,
                                 first_crawl_time, last_crawl_time, crawl_count,
                                 created_at, updated_at)
                                VALUES (?, ?, ?, ?, ?, ?, ?, 1, ?, ?)
                            """, (
                                item.title,
                                platform_id,
                                item.rank,
                                "",
                                item.mobile_url,
                                data.crawl_time,
                                data.crawl_time,
                                now_str,
                                now_str
                            ))
                            new_count += 1

                    except sqlite3.Error as e:
                        print(f"[数据库] 保存新闻条目失败 [{item.title[:30]}...]: {e}")

            # 提交事务
            conn.commit()
            conn.close()

            print(f"[数据库] 保存完成：新增 {new_count} 条，更新 {updated_count} 条")
            return True, new_count, updated_count

        except Exception as e:
            print(f"[数据库] 保存失败: {e}")
            return False, 0, 0

    def get_news_by_date(
        self,
        date: Optional[str] = None,
        platform_id: Optional[str] = None,
        limit: Optional[int] = None,
    ) -> List[Dict]:
        """
        查询指定日期的新闻数据

        Args:
            date: 日期字符串（YYYY-MM-DD），None 表示查询所有日期
            platform_id: 平台ID过滤，None 表示所有平台
            limit: 限制返回数量，None 表示不限制

        Returns:
            新闻条目字典列表
        """
        conn = self._get_connection()
        cursor = conn.cursor()

        try:
            # 构建查询条件
            conditions = []
            params = []

            if date:
                # 根据日期查询（匹配 first_crawl_time 或 last_crawl_time）
                conditions.append("(first_crawl_time LIKE ? OR last_crawl_time LIKE ?)")
                date_pattern = f"{date}%"
                params.extend([date_pattern, date_pattern])

            if platform_id:
                conditions.append("platform_id = ?")
                params.append(platform_id)

            where_clause = "WHERE " + " AND ".join(conditions) if conditions else ""

            # 构建 SQL
            sql = f"""
                SELECT id, title, platform_id, rank, url, mobile_url,
                       first_crawl_time, last_crawl_time, crawl_count,
                       created_at, updated_at
                FROM news_items
                {where_clause}
                ORDER BY last_crawl_time DESC, rank ASC
            """

            if limit:
                sql += f" LIMIT {limit}"

            cursor.execute(sql, params)
            rows = cursor.fetchall()

            # 转换为字典列表
            results = []
            for row in rows:
                results.append({
                    "id": row["id"],
                    "title": row["title"],
                    "platform_id": row["platform_id"],
                    "rank": row["rank"],
                    "url": row["url"],
                    "mobile_url": row["mobile_url"],
                    "first_crawl_time": row["first_crawl_time"],
                    "last_crawl_time": row["last_crawl_time"],
                    "crawl_count": row["crawl_count"],
                    "created_at": row["created_at"],
                    "updated_at": row["updated_at"],
                })

            return results

        finally:
            conn.close()

    def get_latest_news(
        self,
        platform_id: Optional[str] = None,
        limit: int = 50,
    ) -> List[Dict]:
        """
        获取最新的新闻数据

        Args:
            platform_id: 平台ID过滤，None 表示所有平台
            limit: 返回数量限制

        Returns:
            新闻条目字典列表
        """
        # 获取今天的日期
        today = datetime.now().strftime("%Y-%m-%d")
        return self.get_news_by_date(date=today, platform_id=platform_id, limit=limit)

    def get_news_by_platform(
        self,
        platform_id: str,
        limit: Optional[int] = None,
    ) -> List[Dict]:
        """
        获取指定平台的所有新闻

        Args:
            platform_id: 平台ID
            limit: 限制返回数量

        Returns:
            新闻条目字典列表
        """
        return self.get_news_by_date(platform_id=platform_id, limit=limit)

    def search_news(
        self,
        keyword: str,
        platform_id: Optional[str] = None,
        limit: Optional[int] = None,
    ) -> List[Dict]:
        """
        搜索新闻标题

        Args:
            keyword: 搜索关键词
            platform_id: 平台ID过滤，None 表示所有平台
            limit: 限制返回数量

        Returns:
            新闻条目字典列表
        """
        conn = self._get_connection()
        cursor = conn.cursor()

        try:
            conditions = ["title LIKE ?"]
            params = [f"%{keyword}%"]

            if platform_id:
                conditions.append("platform_id = ?")
                params.append(platform_id)

            where_clause = "WHERE " + " AND ".join(conditions)

            sql = f"""
                SELECT id, title, platform_id, rank, url, mobile_url,
                       first_crawl_time, last_crawl_time, crawl_count,
                       created_at, updated_at
                FROM news_items
                {where_clause}
                ORDER BY last_crawl_time DESC, rank ASC
            """

            if limit:
                sql += f" LIMIT {limit}"

            cursor.execute(sql, params)
            rows = cursor.fetchall()

            results = []
            for row in rows:
                results.append({
                    "id": row["id"],
                    "title": row["title"],
                    "platform_id": row["platform_id"],
                    "rank": row["rank"],
                    "url": row["url"],
                    "mobile_url": row["mobile_url"],
                    "first_crawl_time": row["first_crawl_time"],
                    "last_crawl_time": row["last_crawl_time"],
                    "crawl_count": row["crawl_count"],
                    "created_at": row["created_at"],
                    "updated_at": row["updated_at"],
                })

            return results

        finally:
            conn.close()

    def get_statistics(self) -> Dict[str, Any]:
        """
        获取数据库统计信息

        Returns:
            统计信息字典
        """
        conn = self._get_connection()
        cursor = conn.cursor()

        try:
            stats = {}

            # 总记录数
            cursor.execute("SELECT COUNT(*) as total FROM news_items")
            stats["total_items"] = cursor.fetchone()["total"]

            # 按平台统计
            cursor.execute("""
                SELECT platform_id, COUNT(*) as count
                FROM news_items
                GROUP BY platform_id
                ORDER BY count DESC
            """)
            stats["by_platform"] = {
                row["platform_id"]: row["count"]
                for row in cursor.fetchall()
            }

            # 最新抓取时间
            cursor.execute("""
                SELECT MAX(last_crawl_time) as latest_time
                FROM news_items
            """)
            row = cursor.fetchone()
            stats["latest_crawl_time"] = row["latest_time"] if row["latest_time"] else None

            return stats

        finally:
            conn.close()
