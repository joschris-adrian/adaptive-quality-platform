import sys
import os
from unittest.mock import MagicMock

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

class _KafkaError(Exception):
    pass

_kafka_mock = MagicMock()
_kafka_mock.errors.KafkaError = _KafkaError

_pyarrow_mock = MagicMock()
_pyarrow_mock.__version__ = "15.0.0"
_pyarrow_mock.Table = type("Table", (), {})
_pyarrow_mock.RecordBatch = type("RecordBatch", (), {})
_pyarrow_mock.Array = type("Array", (), {})
_pyarrow_mock.ChunkedArray = type("ChunkedArray", (), {})

_pandas_mock = MagicMock()
_pandas_mock.DataFrame = type("DataFrame", (), {})
_pandas_mock.Series = type("Series", (), {})

_polars_mock = MagicMock()
_polars_mock.DataFrame = type("DataFrame", (), {})
_polars_mock.Series = type("Series", (), {})

MOCK_MODULES = [
    "mlflow",
    "mlflow.sklearn",
    "mlflow.tracking",
    "mlflow.tracking.client",
    "mlflow.tracking.MlflowClient",
    "kafka.admin",
    "kafka.admin.client",
    "psycopg2",
    "psycopg2.extras",
    "psycopg2.pool",
    "prometheus_client",
    "uvicorn",
    "opensearch-py",
    "opensearchpy",
    "wandb",
    "apache-airflow",
    "airflow",
    "airflow.models",
    "airflow.operators",
    "airflow.operators.python",
]

for mod in MOCK_MODULES:
    if mod not in sys.modules:
        sys.modules[mod] = MagicMock()

sys.modules["kafka"] = _kafka_mock
sys.modules["kafka.errors"] = _kafka_mock.errors
sys.modules["pyarrow"] = _pyarrow_mock
sys.modules["pandas"] = _pandas_mock
sys.modules["polars"] = _polars_mock