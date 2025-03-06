"""
Streamlit App for Cost Tracker (Open WebUI function) Data Visualization

This Streamlit application processes and visualizes cost data from a JSON file.
It generates plots for total tokens used and total costs by model and user.

Author: bgeneto
Version: 0.2.2
Date: 2024-11-29
"""

import datetime
import json
from typing import Any, Dict, List, Optional

import pandas as pd
import plotly.express as px
import streamlit as st
st.set_page_config(page_title="Cost Tracker App", page_icon="💵")

@st.cache_data
def load_data(file: Any) -> Optional[List[Dict[str, Any]]]:
    """Load data from a JSON file.

    Args:
        file: A file-like object containing JSON data.

    Returns:
        A list of dictionaries with cost records if the JSON is valid, otherwise None.
    """
    try:
        data = json.load(file)
        return data
    except json.JSONDecodeError:
        st.error("Invalid JSON file. Please upload a valid JSON file.")
        return None


def process_data(data: Dict[str, List[Dict[str, Any]]]) -> pd.DataFrame:
    """Process the data by extracting the month, model, cost, and user.

    Args:
        data: A dictionary where keys are user emails and values are lists of cost records.

    Returns:
        A pandas DataFrame with processed data.
    """
    processed_data = []

    for user_email, records in data.items():
        if not isinstance(records, list):  # 🚨 리스트가 아닐 경우 오류 방지
            st.error(f"Invalid data format for user {user_email}")
            continue

        for record in records:
            if not isinstance(record, dict):  # 🚨 잘못된 데이터 필터링
                st.error(f"Invalid record format: {record}")
                continue

            timestamp_str = record.get("timestamp")
            if not timestamp_str or not isinstance(timestamp_str, str):
                st.error(f"Missing or invalid timestamp in record: {record}")
                continue  # 🚨 건너뛰기

            # ✅ 여러 timestamp 포맷 지원
            timestamp = None
            for fmt in ("%Y-%m-%dT%H:%M:%S.%f", "%Y-%m-%dT%H:%M:%S"):
                try:
                    timestamp = datetime.datetime.strptime(timestamp_str, fmt)
                    break
                except ValueError:
                    continue

            if not timestamp:
                st.error(f"Invalid timestamp format: {timestamp_str}")
                continue  # 🚨 건너뛰기

            month = timestamp.strftime("%Y-%m")
            model = record.get("model", "Unknown Model")
            cost = record.get("total_cost", "0")

            try:
                cost = float(cost) if isinstance(cost, (int, float, str)) else 0.0
            except ValueError:
                st.error(f"Invalid cost value for model {model}: {cost}")
                continue  # 🚨 건너뛰기

            total_tokens = record.get("input_tokens", 0) + record.get("output_tokens", 0)

            processed_data.append(
                {
                    "month": month,
                    "model": model,
                    "total_cost": cost,
                    "user": user_email,  # ✅ 사용자 이메일 추가
                    "total_tokens": total_tokens,
                }
            )

    df = pd.DataFrame(processed_data)

    # ✅ DataFrame이 비어 있는 경우 경고 메시지 출력
    if df.empty:
        st.warning("No valid data was processed. Please check your JSON file.")

    return df


def plot_data(data: pd.DataFrame, month: str) -> None:
    """Plot the data for a specific month.

    Args:
        data: A pandas DataFrame containing processed data.
        month: A string representing the month to filter data.
    """
    month_data = data[data["month"] == month]

    if month_data.empty:
        st.error(f"No data available for {month}.")
        return

    # ---------------------------------
    # Model Usage Bar Plot (Total Tokens)
    # ---------------------------------
    month_data_models_tokens = (
        month_data.groupby("model")["total_tokens"].sum().reset_index()
    )
    month_data_models_tokens = month_data_models_tokens.sort_values(
        by="total_tokens", ascending=False
    ).head(10)
    fig_models_tokens = px.bar(
        month_data_models_tokens,
        x="model",
        y="total_tokens",
        title=f"Top 10 Total Tokens Used by Model ({month})",
    )
    st.plotly_chart(fig_models_tokens, use_container_width=True)

    # ---------------------------------
    # Model Cost Bar Plot (Total Cost)
    # ---------------------------------
    month_data_models_cost = (
        month_data.groupby("model")["total_cost"].sum().reset_index()
    )
    month_data_models_cost = month_data_models_cost.sort_values(
        by="total_cost", ascending=False
    ).head(10)
    fig_models_cost = px.bar(
        month_data_models_cost,
        x="model",
        y="total_cost",
        title=f"Top 10 Total Cost by Model ({month})",
    )
    st.plotly_chart(fig_models_cost, use_container_width=True)

    # ---------------------------------
    # User Cost Bar Plot (Total Cost)
    # ---------------------------------
    month_data_users = month_data.groupby("user")["total_cost"].sum().reset_index()
    month_data_users = month_data_users.sort_values(by="total_cost", ascending=False)
    month_data_users["total"] = month_data_users["total_cost"].sum()
    month_data_users = pd.concat(
        [
            month_data_users,
            pd.DataFrame(
                {"user": ["Total"], "total_cost": [month_data_users["total"].iloc[0]]}
            ),
        ]
    )
    fig_users = px.bar(
        month_data_users, x="user", y="total_cost", title=f"Total Cost by User ({month})"
    )
    st.plotly_chart(fig_users, use_container_width=True)

    # ---------------------------------
    # Collapsible DataFrames
    # ---------------------------------
    with st.expander("Show DataFrames"):
        st.subheader("Month Data")
        st.dataframe(month_data)
        st.subheader("Month Data Models Tokens")
        st.dataframe(month_data_models_tokens)
        st.subheader("Month Data Models Cost")
        st.dataframe(month_data_models_cost)
        st.subheader("Month Data Users")
        st.dataframe(month_data_users)


def main():

    st.title("Cost Tracker for Open WebUI")
    st.divider()

    st.page_link(
        "https://github.com/bgeneto/open-webui-cost-tracker/",
        label="GitHub Page",
        icon="🏠",
    )

    st.sidebar.title("⚙️ Options")

    st.info(
        "This Streamlit app processes and visualizes cost data from a JSON file. Select a JSON file below and a month to plot the data."
    )

    file = st.file_uploader("Upload a JSON file", type=["json"])

    if file is not None:
        data = load_data(file)
        if data is not None:
            processed_data = process_data(data)
            months = processed_data["month"].unique()
            month = st.sidebar.selectbox("Select a month", months)
            if st.button("Process Data"):
                plot_data(processed_data, month)
            if st.sidebar.button("Plot Data"):
                plot_data(processed_data, month)

if __name__ == "__main__":
    main()
