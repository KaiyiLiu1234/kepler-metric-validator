from prometheus_api_client import PrometheusConnect
from datetime import datetime
from util import QueryRange, DataPoint
class PromConnect:
    
    def __init__(self, url) -> None:
        self.prom = PrometheusConnect(url=url, disable_ssl=True)

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
