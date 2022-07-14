from concurrent.futures import ThreadPoolExecutor, Future
from typing import Any, Callable


class ParallelExecutor:
    def __init__(self, max_request=300):
        self.__max_request = max_request
        self.__executor = ThreadPoolExecutor(max_workers=max_request)

    def submit(self, request_fn: Callable, response_fn: Callable[[Future], Any]):
        future = self.__executor.submit(request_fn)
        future.add_done_callback(response_fn)
