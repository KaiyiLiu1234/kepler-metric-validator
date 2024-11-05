from prometheus_api_client import PrometheusConnect
from datetime import datetime
from validation import QueryRange, DataPoint
from typing import NamedTuple

class PromConfig(NamedTuple):
    url: str
    disable_ssl: bool

class PromConnect:
    def __init__(self, pc: PromConfig) -> None:
        self.prom = PrometheusConnect(url=pc.url, disable_ssl=pc.disable_ssl)

    def get_metric_range(self, query: str, start: datetime, end: datetime) -> QueryRange:
        series = self.prom.custom_query_range(
            query=query,
            start_time=start,
            end_time=end,
            step="3s"
        )
        values = series[0]['values']
        datapoints = [DataPoint(int(value[0]), float(value[1])) for value in values]
        return QueryRange(
            query=query,
            values=datapoints
        )