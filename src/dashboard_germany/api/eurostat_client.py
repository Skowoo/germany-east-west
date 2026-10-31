
from itertools import product

import httpx
import pandas as pd


BASE_URL = (
    "https://ec.europa.eu/eurostat/api/"
    "dissemination/statistics/1.0/data"
)


def fetch_dataset(
    dataset_code: str,
    params: dict | None = None,
) -> dict:
    request_params = {
        "lang": "EN",
        **(params or {}),
    }

    response = httpx.get(
        f"{BASE_URL}/{dataset_code}",
        params=request_params,
        timeout=60,
    )

    if response.is_error:
        raise RuntimeError(
            f"Eurostat API error ({response.status_code}): {response.text}"
        )

    response.raise_for_status()

    data = response.json()

    if data.get("class") == "error":
        raise RuntimeError(data.get("label", "Eurostat API error"))

    return data



def jsonstat_to_dataframe(data: dict) -> pd.DataFrame:
    dimension_ids = data["id"]
    dimension_sizes = data["size"]
    dimensions = data["dimension"]
    values = data.get("value", {})

    categories = {}

    for dimension_id in dimension_ids:
        category = dimensions[dimension_id]["category"]
        indexes = category["index"]

        if isinstance(indexes, dict):
            ordered_codes = sorted(
                indexes.keys(),
                key=lambda code: indexes[code],
            )
        else:
            ordered_codes = indexes

        labels = category.get("label", {})

        categories[dimension_id] = [
            {
                "code": code,
                "label": labels.get(code, code),
            }
            for code in ordered_codes
        ]

    strides = []

    for index in range(len(dimension_sizes)):
        stride = 1

        for size in dimension_sizes[index + 1:]:
            stride *= size

        strides.append(stride)

    records = []

    for combination in product(
        *(categories[dimension] for dimension in dimension_ids)
    ):
        indexes = [
            dimensions[dimension]["category"]["index"][item["code"]]
            if isinstance(dimensions[dimension]["category"]["index"], dict)
            else item_index
            for dimension, item, item_index in zip(
                dimension_ids,
                combination,
                [
                    next(
                        i for i, category in enumerate(categories[dim])
                        if category["code"] == item["code"]
                    )
                    for dim, item in zip(dimension_ids, combination)
                ],
            )
        ]

        offset = sum(
            item_index * strides[dimension_index]
            for dimension_index, item_index in enumerate(indexes)
        )

        value = (
            values.get(str(offset))
            if isinstance(values, dict)
            else values[offset] if values else None
        )

        record = {
            dimension: item["code"]
            for dimension, item in zip(dimension_ids, combination)
        }

        record["value"] = value

        for dimension, item in zip(dimension_ids, combination):
            record[f"{dimension}_label"] = item["label"]

        records.append(record)

    return pd.DataFrame(records)


def get_gdp_data() -> pd.DataFrame:
    data = fetch_dataset(
        "nama_10r_2gdp",
        {
            "freq": "A",
            "unit": "PPS_EU27_2020_HAB",
            "geoLevel": "nuts2",
            "sinceTimePeriod": "2000",
            "untilTimePeriod": "2024",
        },
    )

    return jsonstat_to_dataframe(data)
