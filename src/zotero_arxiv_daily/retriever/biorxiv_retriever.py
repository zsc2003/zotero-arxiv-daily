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
            raise ValueError(f"category must be specified for {self.name}")

    def _retrieve_raw_papers(self) -> list[dict[str, Any]]:
        api_url = f"https://api.biorxiv.org/details/{self.server}/2d/0/json"
    
        retry_num = 10
        delay_time = 10
    
        for i in range(retry_num):
            try:
                response = requests.get(
                    api_url,
                    timeout=30,
                    headers={
                        "Accept": "application/json",
                    },
                )
                response.raise_for_status()
    
                # JSON 解析必须放进 retry 里面
                result = response.json()
    
                # 确认返回的数据结构确实是 bioRxiv API 的正常结构
                if not isinstance(result, dict) or "collection" not in result:
                    raise ValueError(
                        f"Invalid bioRxiv API response: {str(result)[:300]}"
                    )
    
                break
    
            except Exception as e:
                logger.warning(
                    f"Failed to retrieve bioRxiv papers "
                    f"({i + 1}/{retry_num}): {e}"
                )
    
                # 输出响应信息，方便下次直接判断 bioRxiv 返回了什么
                if "response" in locals():
                    logger.warning(
                        f"bioRxiv response: status={response.status_code}, "
                        f"content-type={response.headers.get('content-type')}, "
                        f"body={response.text[:300]!r}"
                    )
    
                if i == retry_num - 1:
                    logger.error(
                        "bioRxiv retrieval failed after "
                        f"{retry_num} attempts. Skipping bioRxiv."
                    )
                    return []
    
                sleep(delay_time)
    
        collection = result["collection"]

        if len(collection) == 0:
            logger.warning(f"No paper found. API Message: {result['messages']}")
            return []
        all_dates = set(c['date'] for c in collection)
        latest_date = sorted(all_dates)[-1]
        collection = [c for c in collection if c['date'] == latest_date]
        categories = [c.lower() for c in self.retriever_config.category]
        collection = [c for c in collection if c['category'] in categories]
        if self.config.executor.debug:
            collection = collection[:10]
        return collection


    def convert_to_paper(self, raw_paper:dict[str, Any]) -> Paper | None:
        title = raw_paper['title']
        authors = [a.strip() for a in raw_paper['authors'].split(';')]
        abstract = raw_paper['abstract']
        pdf_url = f"https://www.{self.server}.org/content/{raw_paper['doi']}v{raw_paper['version']}.full.pdf"
        full_text = None # biorxiv forbids scraping its pdf
        return Paper(
            source=self.name,
            title=title,
            authors=authors,
            abstract=abstract,
            url=pdf_url,
            pdf_url=pdf_url,
            full_text=full_text
        )
