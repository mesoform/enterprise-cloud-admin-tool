import boto3

from .base import Metrics


class CloudWatchMetrics(Metrics):
    def __init__(self, *args, **kwargs):
        self.namespace = None

        super().__init__(*args, **kwargs)

        self.metrics_client = boto3.client("cloudwatch")

    def process_args(self, args):
        self.namespace = args.monitoring_namespace.upper()

    def send_metrics(self):
        """
        Sends self.prepared_metrics to monitoring system
        :return:
        """
        self.prepare_metrics()
        self.metrics_client.put_metric_data(
            MetricData=list(self.prepared_metrics.values()),
            Namespace=self.namespace,
        )

    def prepare_metrics(self):
        """
        Enriches MetricsRegistry.metrics content and processes data to meet requirements of
        monitoring server and stores it in self.prepared_metrics
        """
        self.units_map = {
            "seconds": "Seconds",
            "minutes": "Minutes",
            "hours": "Hours",
            "days": "Days",
            None: "None",
        }

        for metric_name, metric_dict in self.metrics_registry.metrics.items():
            cloudwatch_metric_name = metric_name.upper()

            self.prepared_metrics[cloudwatch_metric_name] = {
                "MetricName": cloudwatch_metric_name,
                "Dimensions": [
                    {
                        "Name": "metric_set",
                        "Value": self.metrics_registry.metric_set,
                    }
                ],
                "Unit": self.units_map[metric_dict["unit"]],
                "Value": metric_dict["value"],
            }
