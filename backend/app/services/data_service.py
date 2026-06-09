"""Data integration orchestration service."""

from __future__ import annotations

from typing import Dict

from ..integrations import (
    DataForSEODataSource,
    GoogleAnalyticsDataSource,
    GoogleSearchConsoleDataSource,
)


class DataService:
    def __init__(self):
        self.ga = GoogleAnalyticsDataSource()
        self.gsc = GoogleSearchConsoleDataSource()
        self.dfs = DataForSEODataSource()

    def get_ga_top_pages(self) -> Dict:
        return self.ga.fetch()

    def get_gsc_queries(self) -> Dict:
        return self.gsc.fetch()

    def get_dfs_serp(self, keyword: str) -> Dict:
        return self.dfs.fetch(keyword=keyword)
