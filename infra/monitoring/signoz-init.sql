-- SigNoz ClickHouse Schema Init (single-node dev, cluster='cluster')
-- Run with: clickhouse-client --queries-file signoz-init.sql

-- ============================================================
-- signoz_traces
-- ============================================================
CREATE TABLE IF NOT EXISTS signoz_traces.signoz_index_v2 ON CLUSTER 'cluster' (
  timestamp DateTime64(9) CODEC(DoubleDelta, LZ4),
  traceID FixedString(32) CODEC(ZSTD(1)),
  spanID String CODEC(ZSTD(1)),
  parentSpanID String CODEC(ZSTD(1)),
  serviceName LowCardinality(String) CODEC(ZSTD(1)),
  name LowCardinality(String) CODEC(ZSTD(1)),
  kind Int8 CODEC(T64, ZSTD(1)),
  durationNano UInt64 CODEC(T64, ZSTD(1)),
  statusCode Int16 CODEC(T64, ZSTD(1)),
  externalHttpMethod LowCardinality(String) CODEC(ZSTD(1)),
  externalHttpUrl LowCardinality(String) CODEC(ZSTD(1)),
  component LowCardinality(String) CODEC(ZSTD(1)),
  dbSystem LowCardinality(String) CODEC(ZSTD(1)),
  dbName LowCardinality(String) CODEC(ZSTD(1)),
  dbOperation LowCardinality(String) CODEC(ZSTD(1)),
  peerService LowCardinality(String) CODEC(ZSTD(1)),
  events Array(String) CODEC(ZSTD(2)),
  httpMethod LowCardinality(String) CODEC(ZSTD(1)),
  httpUrl LowCardinality(String) CODEC(ZSTD(1)),
  httpCode LowCardinality(String) CODEC(ZSTD(1)),
  httpRoute LowCardinality(String) CODEC(ZSTD(1)),
  httpHost LowCardinality(String) CODEC(ZSTD(1)),
  msgSystem LowCardinality(String) CODEC(ZSTD(1)),
  msgOperation LowCardinality(String) CODEC(ZSTD(1)),
  hasError bool CODEC(T64, ZSTD(1)),
  tagMap Map(LowCardinality(String), String) CODEC(ZSTD(1)),
  gRPCMethod LowCardinality(String) CODEC(ZSTD(1)),
  gRPCCode LowCardinality(String) CODEC(ZSTD(1)),
  responseStatusCode LowCardinality(String) CODEC(ZSTD(1)),
  stringTagMap Map(String, String) CODEC(ZSTD(1)),
  numberTagMap Map(String, Float64) CODEC(ZSTD(1)),
  boolTagMap Map(String, Bool) CODEC(ZSTD(1)),
  isRemote LowCardinality(String) CODEC(ZSTD(1)),
  statusMessage String CODEC(ZSTD(1)),
  statusCodeString LowCardinality(String) CODEC(ZSTD(1)),
  spanKind LowCardinality(String) CODEC(ZSTD(1)),
  PROJECTION timestampSort (SELECT * ORDER BY timestamp),
  INDEX idx_service serviceName TYPE bloom_filter GRANULARITY 4,
  INDEX idx_name name TYPE bloom_filter GRANULARITY 4,
  INDEX idx_kind kind TYPE minmax GRANULARITY 4,
  INDEX idx_duration durationNano TYPE minmax GRANULARITY 1,
  INDEX idx_hasError hasError TYPE set(2) GRANULARITY 1
) ENGINE MergeTree
PARTITION BY toDate(timestamp)
PRIMARY KEY (serviceName, hasError, toStartOfHour(timestamp), name)
ORDER BY (serviceName, hasError, toStartOfHour(timestamp), name, timestamp)
TTL toDateTime(timestamp) + INTERVAL 1296000 SECOND DELETE
SETTINGS index_granularity = 8192;

CREATE TABLE IF NOT EXISTS signoz_traces.distributed_signoz_index_v2 ON CLUSTER 'cluster'
AS signoz_traces.signoz_index_v2
ENGINE = Distributed('cluster', 'signoz_traces', 'signoz_index_v2', cityHash64(traceID));

CREATE TABLE IF NOT EXISTS signoz_traces.signoz_spans ON CLUSTER 'cluster' (
  timestamp DateTime64(9) CODEC(DoubleDelta, LZ4),
  traceID FixedString(32) CODEC(ZSTD(1)),
  model String CODEC(ZSTD(9))
) ENGINE MergeTree
PARTITION BY toDate(timestamp)
ORDER BY traceID
TTL toDateTime(timestamp) + INTERVAL 1296000 SECOND DELETE
SETTINGS index_granularity = 1024;

CREATE TABLE IF NOT EXISTS signoz_traces.distributed_signoz_spans ON CLUSTER 'cluster'
AS signoz_traces.signoz_spans
ENGINE = Distributed('cluster', 'signoz_traces', 'signoz_spans', cityHash64(traceID));

CREATE TABLE IF NOT EXISTS signoz_traces.top_level_operations ON CLUSTER 'cluster' (
  serviceName LowCardinality(String) CODEC(ZSTD(1)),
  name LowCardinality(String) CODEC(ZSTD(1))
) ENGINE = ReplacingMergeTree
ORDER BY (serviceName, name);

CREATE TABLE IF NOT EXISTS signoz_traces.distributed_top_level_operations ON CLUSTER 'cluster'
AS signoz_traces.top_level_operations
ENGINE = Distributed('cluster', 'signoz_traces', 'top_level_operations', cityHash64(serviceName));

CREATE TABLE IF NOT EXISTS signoz_traces.signoz_error_index_v2 ON CLUSTER 'cluster' (
  timestamp DateTime64(9) CODEC(DoubleDelta, LZ4),
  errorID FixedString(32) CODEC(ZSTD(1)),
  groupID FixedString(32) CODEC(ZSTD(1)),
  traceID FixedString(32) CODEC(ZSTD(1)),
  spanID String CODEC(ZSTD(1)),
  serviceName LowCardinality(String) CODEC(ZSTD(1)),
  exceptionType LowCardinality(String) CODEC(ZSTD(1)),
  exceptionMsg String CODEC(ZSTD(1)),
  exceptionStacktrace String CODEC(ZSTD(1)),
  exceptionEscaped bool CODEC(T64, ZSTD(1)),
  resourceTagsMap Map(LowCardinality(String), String) CODEC(ZSTD(1)),
  INDEX idx_errorID errorID TYPE bloom_filter GRANULARITY 4,
  INDEX idx_traceID traceID TYPE bloom_filter GRANULARITY 4,
  INDEX idx_groupID groupID TYPE bloom_filter GRANULARITY 4
) ENGINE MergeTree
PARTITION BY toDate(timestamp)
ORDER BY (serviceName, timestamp, groupID)
TTL toDateTime(timestamp) + INTERVAL 1296000 SECOND DELETE
SETTINGS index_granularity = 8192;

CREATE TABLE IF NOT EXISTS signoz_traces.distributed_signoz_error_index_v2 ON CLUSTER 'cluster'
AS signoz_traces.signoz_error_index_v2
ENGINE = Distributed('cluster', 'signoz_traces', 'signoz_error_index_v2', cityHash64(traceID));

CREATE TABLE IF NOT EXISTS signoz_traces.usage ON CLUSTER 'cluster' (
  tenant String CODEC(ZSTD(1)),
  collector_id String CODEC(ZSTD(1)),
  exporter_id String CODEC(ZSTD(1)),
  timestamp DateTime CODEC(DoubleDelta, LZ4),
  data UInt64 CODEC(T64, ZSTD(1))
) ENGINE MergeTree
ORDER BY (tenant, collector_id, exporter_id, timestamp);

CREATE TABLE IF NOT EXISTS signoz_traces.distributed_usage ON CLUSTER 'cluster'
AS signoz_traces.usage
ENGINE = Distributed('cluster', 'signoz_traces', 'usage', cityHash64(tenant));

-- signoz_index_v3 (newer schema for spans)
CREATE TABLE IF NOT EXISTS signoz_traces.signoz_index_v3 ON CLUSTER 'cluster' (
  ts_bucket_start UInt64 CODEC(DoubleDelta, LZ4),
  resource_fingerprint String CODEC(ZSTD(1)),
  timestamp DateTime64(9) CODEC(DoubleDelta, LZ4),
  traceID FixedString(32) CODEC(ZSTD(1)),
  spanID String CODEC(ZSTD(1)),
  traceState String CODEC(ZSTD(1)),
  parentSpanID String CODEC(ZSTD(1)),
  flags UInt32 CODEC(T64, ZSTD(1)),
  name LowCardinality(String) CODEC(ZSTD(1)),
  kind Int8 CODEC(T64, ZSTD(1)),
  spanKind LowCardinality(String) CODEC(ZSTD(1)),
  durationNano UInt64 CODEC(T64, ZSTD(1)),
  statusCode Int16 CODEC(T64, ZSTD(1)),
  statusMessage String CODEC(ZSTD(1)),
  statusCodeString LowCardinality(String) CODEC(ZSTD(1)),
  attributesString Map(LowCardinality(String), String) CODEC(ZSTD(1)),
  attributesNumber Map(LowCardinality(String), Float64) CODEC(ZSTD(1)),
  attributesBool Map(LowCardinality(String), Bool) CODEC(ZSTD(1)),
  resourcesString Map(LowCardinality(String), String) CODEC(ZSTD(1)),
  events Array(String) CODEC(ZSTD(2)),
  links String CODEC(ZSTD(1)),
  INDEX idx_traceID traceID TYPE bloom_filter GRANULARITY 4,
  INDEX idx_name name TYPE bloom_filter GRANULARITY 4,
  INDEX idx_kind kind TYPE minmax GRANULARITY 4,
  INDEX idx_duration durationNano TYPE minmax GRANULARITY 1
) ENGINE MergeTree
PARTITION BY toDate(timestamp)
PRIMARY KEY (ts_bucket_start, resource_fingerprint, toStartOfHour(timestamp), name)
ORDER BY (ts_bucket_start, resource_fingerprint, toStartOfHour(timestamp), name, timestamp)
TTL toDateTime(timestamp) + INTERVAL 1296000 SECOND DELETE
SETTINGS index_granularity = 8192;

CREATE TABLE IF NOT EXISTS signoz_traces.distributed_signoz_index_v3 ON CLUSTER 'cluster'
AS signoz_traces.signoz_index_v3
ENGINE = Distributed('cluster', 'signoz_traces', 'signoz_index_v3', cityHash64(traceID));

-- ============================================================
-- signoz_metrics
-- ============================================================
CREATE TABLE IF NOT EXISTS signoz_metrics.time_series_v4 ON CLUSTER 'cluster' (
  env LowCardinality(String) DEFAULT 'default',
  temporality LowCardinality(String) DEFAULT 'Unspecified',
  metric_name LowCardinality(String),
  description LowCardinality(String) DEFAULT '',
  unit LowCardinality(String) DEFAULT '',
  type LowCardinality(String) DEFAULT '',
  is_monotonic bool DEFAULT false,
  fingerprint UInt64 CODEC(Delta, ZSTD),
  unix_milli Int64 CODEC(Delta, ZSTD),
  labels String CODEC(ZSTD(5))
) ENGINE = ReplacingMergeTree
PARTITION BY toDate(unix_milli / 1000)
ORDER BY (env, temporality, metric_name, fingerprint);

CREATE TABLE IF NOT EXISTS signoz_metrics.distributed_time_series_v4 ON CLUSTER 'cluster'
AS signoz_metrics.time_series_v4
ENGINE = Distributed('cluster', 'signoz_metrics', 'time_series_v4', cityHash64(env, temporality, metric_name, fingerprint));

CREATE TABLE IF NOT EXISTS signoz_metrics.time_series_v4_6hrs ON CLUSTER 'cluster'
AS signoz_metrics.time_series_v4
ENGINE = ReplacingMergeTree
PARTITION BY toDate(unix_milli / 1000)
ORDER BY (env, temporality, metric_name, fingerprint);

CREATE TABLE IF NOT EXISTS signoz_metrics.distributed_time_series_v4_6hrs ON CLUSTER 'cluster'
AS signoz_metrics.time_series_v4_6hrs
ENGINE = Distributed('cluster', 'signoz_metrics', 'time_series_v4_6hrs', cityHash64(env, temporality, metric_name, fingerprint));

CREATE TABLE IF NOT EXISTS signoz_metrics.time_series_v4_1day ON CLUSTER 'cluster'
AS signoz_metrics.time_series_v4
ENGINE = ReplacingMergeTree
PARTITION BY toDate(unix_milli / 1000)
ORDER BY (env, temporality, metric_name, fingerprint);

CREATE TABLE IF NOT EXISTS signoz_metrics.distributed_time_series_v4_1day ON CLUSTER 'cluster'
AS signoz_metrics.time_series_v4_1day
ENGINE = Distributed('cluster', 'signoz_metrics', 'time_series_v4_1day', cityHash64(env, temporality, metric_name, fingerprint));

CREATE TABLE IF NOT EXISTS signoz_metrics.time_series_v4_1week ON CLUSTER 'cluster'
AS signoz_metrics.time_series_v4
ENGINE = ReplacingMergeTree
PARTITION BY toDate(unix_milli / 1000)
ORDER BY (env, temporality, metric_name, fingerprint);

CREATE TABLE IF NOT EXISTS signoz_metrics.distributed_time_series_v4_1week ON CLUSTER 'cluster'
AS signoz_metrics.time_series_v4_1week
ENGINE = Distributed('cluster', 'signoz_metrics', 'time_series_v4_1week', cityHash64(env, temporality, metric_name, fingerprint));

CREATE TABLE IF NOT EXISTS signoz_metrics.samples_v4 ON CLUSTER 'cluster' (
  env LowCardinality(String) DEFAULT 'default',
  temporality LowCardinality(String) DEFAULT 'Unspecified',
  metric_name LowCardinality(String),
  fingerprint UInt64 CODEC(Delta, ZSTD),
  unix_milli Int64 CODEC(Delta, ZSTD),
  value Float64 CODEC(Gorilla, ZSTD)
) ENGINE MergeTree
PARTITION BY toDate(unix_milli / 1000)
ORDER BY (env, temporality, metric_name, fingerprint, unix_milli)
TTL toDateTime(unix_milli / 1000) + INTERVAL 2592000 SECOND DELETE;

CREATE TABLE IF NOT EXISTS signoz_metrics.distributed_samples_v4 ON CLUSTER 'cluster'
AS signoz_metrics.samples_v4
ENGINE = Distributed('cluster', 'signoz_metrics', 'samples_v4', cityHash64(env, temporality, metric_name, fingerprint));

CREATE TABLE IF NOT EXISTS signoz_metrics.samples_v4_agg_5m ON CLUSTER 'cluster' (
  env LowCardinality(String) DEFAULT 'default',
  temporality LowCardinality(String) DEFAULT 'Unspecified',
  metric_name LowCardinality(String),
  fingerprint UInt64 CODEC(Delta, ZSTD),
  unix_milli Int64 CODEC(Delta, ZSTD),
  value AggregateFunction(sum, Float64),
  le Float64 CODEC(ZSTD(1))
) ENGINE AggregatingMergeTree
PARTITION BY toDate(unix_milli / 1000)
ORDER BY (env, temporality, metric_name, fingerprint, unix_milli, le)
TTL toDateTime(unix_milli / 1000) + INTERVAL 2592000 SECOND DELETE;

CREATE TABLE IF NOT EXISTS signoz_metrics.distributed_samples_v4_agg_5m ON CLUSTER 'cluster'
AS signoz_metrics.samples_v4_agg_5m
ENGINE = Distributed('cluster', 'signoz_metrics', 'samples_v4_agg_5m', cityHash64(env, temporality, metric_name, fingerprint));

CREATE TABLE IF NOT EXISTS signoz_metrics.samples_v4_agg_30m ON CLUSTER 'cluster'
AS signoz_metrics.samples_v4_agg_5m
ENGINE AggregatingMergeTree
PARTITION BY toDate(unix_milli / 1000)
ORDER BY (env, temporality, metric_name, fingerprint, unix_milli, le)
TTL toDateTime(unix_milli / 1000) + INTERVAL 2592000 SECOND DELETE;

CREATE TABLE IF NOT EXISTS signoz_metrics.distributed_samples_v4_agg_30m ON CLUSTER 'cluster'
AS signoz_metrics.samples_v4_agg_30m
ENGINE = Distributed('cluster', 'signoz_metrics', 'samples_v4_agg_30m', cityHash64(env, temporality, metric_name, fingerprint));

CREATE TABLE IF NOT EXISTS signoz_metrics.exp_hist ON CLUSTER 'cluster' (
  env LowCardinality(String) DEFAULT 'default',
  temporality LowCardinality(String) DEFAULT 'Unspecified',
  metric_name LowCardinality(String),
  fingerprint UInt64 CODEC(Delta, ZSTD),
  unix_milli Int64 CODEC(Delta, ZSTD),
  count UInt64 CODEC(Delta, ZSTD),
  sum Float64 CODEC(Gorilla, ZSTD),
  min Float64 CODEC(Gorilla, ZSTD),
  max Float64 CODEC(Gorilla, ZSTD),
  sketch AggregateFunction(quantilesDD(0.01), Float64)
) ENGINE AggregatingMergeTree
PARTITION BY toDate(unix_milli / 1000)
ORDER BY (env, temporality, metric_name, fingerprint, unix_milli)
TTL toDateTime(unix_milli / 1000) + INTERVAL 2592000 SECOND DELETE;

CREATE TABLE IF NOT EXISTS signoz_metrics.distributed_exp_hist ON CLUSTER 'cluster'
AS signoz_metrics.exp_hist
ENGINE = Distributed('cluster', 'signoz_metrics', 'exp_hist', cityHash64(env, temporality, metric_name, fingerprint));

-- ============================================================
-- signoz_logs
-- ============================================================
CREATE TABLE IF NOT EXISTS signoz_logs.logs ON CLUSTER 'cluster' (
  timestamp UInt64 CODEC(DoubleDelta, LZ4),
  observed_timestamp UInt64 CODEC(DoubleDelta, LZ4),
  id String CODEC(ZSTD(1)),
  trace_id String CODEC(ZSTD(1)),
  span_id String CODEC(ZSTD(1)),
  trace_flags UInt32,
  severity_text LowCardinality(String) CODEC(ZSTD(1)),
  severity_number UInt8,
  body String CODEC(ZSTD(2)),
  resources_string_key Array(String) CODEC(ZSTD(1)),
  resources_string_value Array(String) CODEC(ZSTD(1)),
  attributes_string_key Array(String) CODEC(ZSTD(1)),
  attributes_string_value Array(String) CODEC(ZSTD(1)),
  attributes_int64_key Array(String) CODEC(ZSTD(1)),
  attributes_int64_value Array(Int64) CODEC(ZSTD(1)),
  attributes_float64_key Array(String) CODEC(ZSTD(1)),
  attributes_float64_value Array(Float64) CODEC(ZSTD(1)),
  attributes_bool_key Array(String) CODEC(ZSTD(1)),
  attributes_bool_value Array(Bool) CODEC(ZSTD(1)),
  INDEX body_idx body TYPE ngrambf_v1(4, 60000, 5, 0) GRANULARITY 1
) ENGINE MergeTree
PARTITION BY toDate(timestamp / 1000000000)
ORDER BY (timestamp, id)
TTL toDateTime(timestamp / 1000000000) + INTERVAL 1296000 SECOND DELETE;

CREATE TABLE IF NOT EXISTS signoz_logs.distributed_logs ON CLUSTER 'cluster'
AS signoz_logs.logs
ENGINE = Distributed('cluster', 'signoz_logs', 'logs', cityHash64(id));

CREATE TABLE IF NOT EXISTS signoz_logs.logs_v2_resource ON CLUSTER 'cluster' (
  labels String CODEC(ZSTD(5)),
  fingerprint String CODEC(ZSTD(1)),
  seen_at_ts_bucket_start Int64 CODEC(Delta(8), ZSTD(1)),
  INDEX idx_labels lower(labels) TYPE ngrambf_v1(4, 1024, 3, 0) GRANULARITY 1
) ENGINE ReplacingMergeTree
PARTITION BY toDate(seen_at_ts_bucket_start / 1000)
ORDER BY (labels, fingerprint, seen_at_ts_bucket_start)
TTL toDateTime(seen_at_ts_bucket_start) + INTERVAL 1296000 SECOND + INTERVAL 1800 SECOND DELETE
SETTINGS ttl_only_drop_parts = 1, index_granularity = 8192;

CREATE TABLE IF NOT EXISTS signoz_logs.distributed_logs_v2_resource ON CLUSTER 'cluster' (
  labels String CODEC(ZSTD(5)),
  fingerprint String CODEC(ZSTD(1)),
  seen_at_ts_bucket_start Int64 CODEC(Delta(8), ZSTD(1))
) ENGINE = Distributed('cluster', 'signoz_logs', 'logs_v2_resource', cityHash64(labels, fingerprint));

CREATE TABLE IF NOT EXISTS signoz_logs.logs_v2 ON CLUSTER 'cluster' (
  ts_bucket_start UInt64 CODEC(DoubleDelta, LZ4),
  resource_fingerprint String CODEC(ZSTD(1)),
  timestamp UInt64 CODEC(DoubleDelta, LZ4),
  observed_timestamp UInt64 CODEC(DoubleDelta, LZ4),
  id String CODEC(ZSTD(1)),
  trace_id String CODEC(ZSTD(1)),
  span_id String CODEC(ZSTD(1)),
  trace_flags UInt32,
  severity_text LowCardinality(String) CODEC(ZSTD(1)),
  severity_number UInt8,
  body String CODEC(ZSTD(2)),
  attributes_string Map(LowCardinality(String), String) CODEC(ZSTD(1)),
  attributes_number Map(LowCardinality(String), Float64) CODEC(ZSTD(1)),
  attributes_bool Map(LowCardinality(String), Bool) CODEC(ZSTD(1)),
  resources_string Map(LowCardinality(String), String) CODEC(ZSTD(1)),
  scope_name String CODEC(ZSTD(1)),
  scope_version String CODEC(ZSTD(1)),
  scope_string Map(LowCardinality(String), String) CODEC(ZSTD(1)),
  INDEX body_idx lower(body) TYPE ngrambf_v1(4, 60000, 5, 0) GRANULARITY 1,
  INDEX id_minmax id TYPE minmax GRANULARITY 1,
  INDEX severity_number_idx severity_number TYPE set(25) GRANULARITY 4,
  INDEX severity_text_idx severity_text TYPE set(25) GRANULARITY 4
) ENGINE MergeTree
PARTITION BY toDate(timestamp / 1000000000)
ORDER BY (ts_bucket_start, resource_fingerprint, severity_text, timestamp, id)
TTL toDateTime(timestamp / 1000000000) + INTERVAL 1296000 SECOND DELETE
SETTINGS ttl_only_drop_parts = 1, index_granularity = 8192;

CREATE TABLE IF NOT EXISTS signoz_logs.distributed_logs_v2 ON CLUSTER 'cluster' (
  ts_bucket_start UInt64 CODEC(DoubleDelta, LZ4),
  resource_fingerprint String CODEC(ZSTD(1)),
  timestamp UInt64 CODEC(DoubleDelta, LZ4),
  observed_timestamp UInt64 CODEC(DoubleDelta, LZ4),
  id String CODEC(ZSTD(1)),
  trace_id String CODEC(ZSTD(1)),
  span_id String CODEC(ZSTD(1)),
  trace_flags UInt32,
  severity_text LowCardinality(String) CODEC(ZSTD(1)),
  severity_number UInt8,
  body String CODEC(ZSTD(2)),
  attributes_string Map(LowCardinality(String), String) CODEC(ZSTD(1)),
  attributes_number Map(LowCardinality(String), Float64) CODEC(ZSTD(1)),
  attributes_bool Map(LowCardinality(String), Bool) CODEC(ZSTD(1)),
  resources_string Map(LowCardinality(String), String) CODEC(ZSTD(1)),
  scope_name String CODEC(ZSTD(1)),
  scope_version String CODEC(ZSTD(1)),
  scope_string Map(LowCardinality(String), String) CODEC(ZSTD(1))
) ENGINE = Distributed('cluster', 'signoz_logs', 'logs_v2', cityHash64(id));

CREATE TABLE IF NOT EXISTS signoz_logs.tag_attributes ON CLUSTER 'cluster' (
  timestamp DateTime CODEC(DoubleDelta, LZ4),
  tagKey String CODEC(ZSTD(1)),
  tagType Enum('tag' = 1, 'resource' = 2) CODEC(ZSTD(1)),
  tagDataType Enum('string' = 1, 'bool' = 2, 'int64' = 3, 'float64' = 4) CODEC(ZSTD(1)),
  stringTagValue String CODEC(ZSTD(1)),
  int64TagValue Nullable(Int64) CODEC(ZSTD(1)),
  float64TagValue Nullable(Float64) CODEC(ZSTD(1))
) ENGINE ReplacingMergeTree
PARTITION BY toDate(timestamp)
ORDER BY (tagKey, tagType, tagDataType, stringTagValue)
TTL toDateTime(timestamp) + INTERVAL 172800 SECOND DELETE;

CREATE TABLE IF NOT EXISTS signoz_logs.distributed_tag_attributes ON CLUSTER 'cluster'
AS signoz_logs.tag_attributes
ENGINE = Distributed('cluster', 'signoz_logs', 'tag_attributes', cityHash64(tagKey));
