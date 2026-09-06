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

    retry_num = 3
    page_size = 30
    cursor = 0
    collection = []

    while True:
        api_url = (
            f"https://api.biorxiv.org/details/{self.server}/"
            f"{start_date.isoformat()}/{end_date.isoformat()}/"
            f"{cursor}/json"
        )

        logger.debug(
            f"Retrieving {self.server} papers from: {api_url}"
        )

        result = None

        for attempt in range(retry_num):
            try:
                response = requests.get(
                    api_url,
                    timeout=30,
                )
                response.raise_for_status()
                result = response.json()
                break

            except Exception as e:
                if attempt == retry_num - 1:
                    logger.error(
                        f"Failed to retrieve {self.server} papers "
                        f"after {retry_num} attempts: {e}. "
                        f"Skipping {self.server}."
                    )
                    return []

                delay_time = 5 * (attempt + 1)

                logger.warning(
                    f"Failed to retrieve {self.server} papers: {e}. "
                    f"Retry in {delay_time} seconds."
                )

                sleep(delay_time)

        batch = result.get("collection", [])

        if not batch:
            if cursor == 0:
                logger.warning(
                    f"No paper found. API Message: "
                    f"{result.get('messages', [])}"
                )
            break

        collection.extend(batch)

        # bioRxiv API returns at most 30 records per page.
        if len(batch) < page_size:
            break

        cursor += page_size

    if not collection:
        return []

    dated_collection = [
        (
            datetime.strptime(
                c["date"],
                "%Y-%m-%d",
            ).date(),
            c,
        )
        for c in collection
        if c.get("date")
    ]

    if not dated_collection:
        logger.warning(
            f"No valid dated papers returned from {self.server}"
        )
        return []

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
        if c.get("category", "").lower() in categories
    ]

    if self.config.executor.debug:
        collection = collection[:10]

    return collection
