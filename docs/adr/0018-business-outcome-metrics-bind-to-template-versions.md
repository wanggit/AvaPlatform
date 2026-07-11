# Business Outcome Metrics bind to Job Template Versions

MVP tracks business value through Business Outcome Metrics bound to Job Template Versions. A Metric Binding freezes the metric source, baseline, target, direction, attribution window, and owner for that template version so historical comparisons remain meaningful.

Metric sources are intentionally simple: platform-native metrics from Platform events, business-system metrics captured through Tool Gateway integrations, and manual or imported metrics for systems not yet integrated. Each Pilot Job Template should bind at least three Business Outcome Metrics, including at least one platform-native metric.

The MVP should not build a full BI system. It should provide a metric catalog, template-version bindings, platform-native computation, and manual/imported values. Automatic business-system collection grows only where Tool Gateway integrations already exist.
