import boto3

from .base import Metrics


class CloudWatchMetrics(Metrics):
    def __init__(self, *args, **kwargs):
        self.namespace = None

        super().__init__(*args, **kwargs)

        self.metrics_client = boto3.client("cloudwatch")

    def process_args(self, args):
        """
        Method for processing info, that came from cli, such as
        credentials data or platform-specific arguments
        """
        self.namespace = args.monitoring_namespace.upper()

    def send_metrics(self):
        """
        Sends self.prepared_metrics to monitoring system
        :return:
        """
        self.prepare_metrics()

        metric_data = []

        for metric_name, metric_dict in self.prepared_metrics.items():
            metric_data.append({
                "MetricName": metric_name,
                "Dimensions": metric_dict["dimensions"],
                "Unit": metric_dict["unit"],
                "Value": metric_dict["value"]
            })

        self.metrics_client.put_metric_data(
            MetricData=metric_data,
            Namespace=self.namespace
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
            None: "None"
        }

        for metric_name, metric_dict in self.metrics_registry.metrics.items():
            prepared_metric_dict = metric_dict.copy()

            prepared_metric_dict["unit"] = self.units_map[
                prepared_metric_dict["unit"]]

            prepared_metric_dict["dimensions"] = [
                {
                    "Name": "metric_set",
                    "Value": self.metrics_registry.metric_set
                },
            ]

            cloudwatch_metric_name = metric_name.upper()
            self.prepared_metrics[cloudwatch_metric_name] = prepared_metric_dict
