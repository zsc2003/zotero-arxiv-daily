from datetime import datetime, timedelta, timezone

import requests
from .base import BaseRetriever, register_retriever
from ..protocol import Paper
from loguru import logger
from typing import Any
from time import sleep


@register_retriever("biorxiv")
class BiorxivRetriever(BaseRetriever):
    server = "biorxiv"

    def __init__(self, config):
        super().__init__(config)
        if self.retriever_config.category is None:
            raise ValueError(
                f"category must be specified for {self.name}"
            )

    def _retrieve_raw_papers(self) -> list[dict[str, Any]]:
        end_date = datetime.now(timezone.utc).date()
        start_date = end_date - timedelta(days=2)

        api_url = (
            f"https://api.biorxiv.org/details/{self.server}/"
            f"{start_date.isoformat()}/{end_date.isoformat()}"
        )

        logger.debug(
            f"Retrieving {self.server} papers from: {api_url}"
        )

        retry_num = 10
        delay_time = 10

        for i in range(retry_num):
            try:
                response = requests.get(
                    api_url,
                    timeout=30,
                )
                response.raise_for_status()
                break

            except Exception as e:
                if i == retry_num - 1:
                    raise e

                logger.warning(
                    f"Failed to retrieve papers: {str(e)}. "
                    f"Retry in {delay_time} seconds."
                )
                sleep(delay_time)

        result = response.json()
        collection = result['collection']

        if len(collection) == 0:
            logger.warning(
                f"No paper found. API Message: "
                f"{result['messages']}"
            )
            return []

        dated_collection = [
            (
                datetime.strptime(
                    c['date'],
                    "%Y-%m-%d"
                ).date(),
                c
            )
            for c in collection
        ]

        latest_date = max(
            date for date, _ in dated_collection
        )

        collection = [
            c
            for date, c in dated_collection
            if date == latest_date
        ]

        categories = [
            c.lower()
            for c in self.retriever_config.category
        ]

        collection = [
            c
            for c in collection
            if c['category'] in categories
        ]

        if self.config.executor.debug:
            collection = collection[:10]

        return collection
