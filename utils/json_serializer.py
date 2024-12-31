import json
import uuid
from datetime import datetime
import pandas as pd
import numpy as np
from decimal import Decimal


class JSONSerializer(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, pd.Timestamp):
            return obj.isoformat()
        elif isinstance(obj, datetime):
            return obj.isoformat()
        elif isinstance(obj, pd.Series):
            return obj.to_dict()
        elif isinstance(obj, np.integer):
            return int(obj)
        elif isinstance(obj, np.floating):
            return float(obj)
        elif isinstance(obj, np.ndarray):
            return obj.tolist()
        elif isinstance(obj, Decimal):
            return float(obj)
        elif pd.isna(obj):
            return None
        return super().default(obj)


def convert_dataframe_for_json(df):
    """Convert DataFrame to JSON-serializable format with proper encoding"""
    if df is None or df.empty:
        return []

    # Convert DataFrame to records
    records = df.to_dict("records")

    # Convert using custom JSONSerializer
    return json.loads(json.dumps(records, cls=JSONSerializer, ensure_ascii=False))


def prepare_trace_data(input_data, output_data=None, error=None):
    try:
        trace_data = {
            "id": str(uuid.uuid4()),
            "trace_type": "process",
            "meta_data": {
                "input": input_data,
                "task": output_data.get("task") if output_data else None,
                "plan_string": output_data.get("plan_string") if output_data else None,
                "steps": output_data.get("steps") if output_data else None,
                "results": output_data.get("results") if output_data else None,
                "result": output_data.get("result") if output_data else None,
                "calc_data": output_data.get("calc_data") if output_data else None,
                "timestamp": datetime.utcnow().isoformat(),
            },
            "duration_ms": 0.0,
            "token_usage": 0,
            "model": "unknown",
        }

        # DataFrame handling - store only column information
        if output_data and "dataframes" in output_data:
            dataframe_info = {}
            for k, df in output_data["dataframes"].items():
                if isinstance(df, pd.DataFrame):
                    dataframe_info[k] = {
                        "columns": list(df.columns),
                        "shape": df.shape,
                        "dtypes": {col: str(dtype) for col, dtype in df.dtypes.items()},
                    }
                else:
                    dataframe_info[k] = None
            trace_data["meta_data"]["dataframes"] = dataframe_info

        if error:
            trace_data["meta_data"]["status"] = "error"
            trace_data["meta_data"]["error"] = str(error)

        return json.loads(
            json.dumps(trace_data, cls=JSONSerializer, ensure_ascii=False)
        )

    except Exception as e:
        return {
            "id": str(uuid.uuid4()),
            "trace_type": "error",
            "meta_data": {
                "input": str(input_data),
                "status": "error",
                "error": "Error preparing trace data",
                "timestamp": datetime.utcnow().isoformat(),
            },
            "duration_ms": 0.0,
            "token_usage": 0,
            "model": "unknown",
        }
