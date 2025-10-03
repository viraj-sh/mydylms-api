# core/pagination.py
from math import ceil
from fastapi import HTTPException


def paginate_list(items: list, page: int = 1, page_size: int = 20):
    total = len(items)
    total_pages = ceil(total / page_size)
    if page > total_pages and total_pages != 0:
        raise HTTPException(
            status_code=404,
            detail=f"Page {page} out of range. Total pages: {total_pages}",
        )
    start = (page - 1) * page_size
    end = start + page_size
    return {
        "items": items[start:end],
        "pagination": {
            "page": page,
            "page_size": page_size,
            "total_items": total,
            "total_pages": total_pages,
        },
    }
