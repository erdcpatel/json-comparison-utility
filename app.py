import streamlit as st
import pandas as pd
import json
from json_comparison import (
    compare_json_objects,
    compare_json_lists,
    is_json_list_of_objects,
    get_all_keys,
    get_potential_join_keys
)
from api_utils import APIHandler
from state_utils import init_session_state, get_current_comparison_state
from display_utils import get_distinct_exclusion_keys, apply_filters, highlight_diff
from typing import Optional, Dict, Any
import logging

# Add to the top of the file
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


# Initialize session state
init_session_state()

# Configuration
st.set_page_config(layout="wide", page_title="JSON Comparison Utility")
st.title("📊 JSON Comparison Utility")


def load_json(file) -> Optional[Dict]:
    """Load JSON from file"""
    try:
        return json.load(file)
    except json.JSONDecodeError:
        st.error("❌ Invalid JSON file. Please upload a valid JSON file.")
        return None
    except Exception as e:
        st.error(f"❌ Error loading file: {str(e)}")
        return None


def api_config_form(side: str, tab_name: str) -> Dict[str, Any]:
    """Render API configuration form for one side"""
    state = get_current_comparison_state(tab_name)

    with st.expander(f"⚙️ {side.capitalize()} API Configuration", expanded=True):
        method = st.selectbox(
            "HTTP Method",
            ["GET", "POST"],
            key=f"{tab_name}_{side}_method"
        )

        url = st.text_input(
            "API Endpoint URL",
            key=f"{tab_name}_{side}_url"
        )

        headers = st.text_area(
            "Request Headers (JSON)",
            value='{"Content-Type": "application/json"}',
            key=f"{tab_name}_{side}_headers"
        )

        if method == "POST":
            body = st.text_area(
                "Request Body (JSON)",
                value='{}',
                key=f"{tab_name}_{side}_body"
            )
        else:
            body = None
            params = st.text_area(
                "Query Parameters (JSON)",
                value='{}',
                key=f"{tab_name}_{side}_params"
            )

        if st.button(f"🔌 Fetch {side.capitalize()} Data", key=f"{tab_name}_fetch_{side}"):
            try:
                headers_json = json.loads(headers) if headers else {}
                body_json = json.loads(body) if body else None
                params_json = json.loads(params) if method == "GET" and params else None

                with st.spinner(f"Fetching {side} data..."):
                    data = APIHandler.fetch_json(
                        url=url,
                        method=method,
                        headers=headers_json,
                        body=body_json,
                        params=params_json
                    )
                    state[f"{side}_data"] = data
                    st.success(f"✅ Successfully fetched {side} data!")
                    return data

            except Exception as e:
                st.error(f"❌ Failed to fetch {side} data: {str(e)}")
                return None

    return None


def display_results(tab_name: str, filters: list):
    """Display comparison results with current filters"""
    state = get_current_comparison_state(tab_name)

    if not state['results']:
        st.warning("No comparison results available")
        return

    filtered_results = apply_filters(state['results'], filters)

    if not filtered_results:
        st.success("✅ No differences found after filtering!")
        return

    # Convert to DataFrame and display
    df = pd.DataFrame(filtered_results)
    styled_df = df.style.apply(highlight_diff, axis=1)
    st.dataframe(styled_df, use_container_width=True, height=600)

    # Download button with unique key
    st.download_button(
        label="📥 Download Filtered Results as CSV",
        data=df.to_csv(index=False).encode('utf-8'),
        file_name='filtered_comparison.csv',
        mime='text/csv',
        use_container_width=True,
        key=f"{tab_name}_download_button"
    )


# User Guide
with st.expander("ℹ️ How to use this utility", expanded=False):
    st.markdown("""
    **JSON comparison tool**

    ### Features:
    - Completely isolated state between File and API tabs
    - Real-time filtering that works instantly
    - Smart join key detection (only for arrays)
    - Independent filters for each tab
    """)

# Main tabs
tab1, tab2 = st.tabs(["📁 File Comparison", "🌐 API Comparison"])

with tab1:
    st.subheader("Compare JSON Files")
    col1, col2 = st.columns(2)
    state = get_current_comparison_state("file")

    with col1:
        left_file = st.file_uploader("Left JSON File", type=['json'], key="left_file")

    with col2:
        right_file = st.file_uploader("Right JSON File", type=['json'], key="right_file")

    if left_file and right_file:
        left_json = load_json(left_file)
        right_json = load_json(right_file)

        if left_json and right_json:
            state['all_keys'] = set()
            state['all_keys'].update(get_all_keys(left_json))
            state['all_keys'].update(get_all_keys(right_json))

            if is_json_list_of_objects(left_json) and is_json_list_of_objects(right_json):
                state['potential_join_keys'] = get_potential_join_keys(left_json, right_json)

            with st.container():
                st.subheader("Comparison Options")

                if state['potential_join_keys']:
                    join_key = st.selectbox(
                        "Join Key (optional)",
                        options=[""] + state['potential_join_keys'],
                        help="Select a key to match objects in arrays",
                        key="file_join_key"
                    )
                else:
                    join_key = None

            if st.button("🔍 Compare JSON Files", use_container_width=True, key="file_compare_button"):
                with st.spinner("Comparing JSON files..."):
                    if is_json_list_of_objects(left_json) and is_json_list_of_objects(right_json) and join_key:
                        state['results'] = compare_json_lists(left_json, right_json, join_key)
                    else:
                        state['results'] = compare_json_objects(left_json, right_json)

                    state['excluded_keys'] = []
                    st.success("✅ Comparison complete!")

    elif left_file or right_file:
        st.warning("⚠️ Please upload both files to compare")

    if state['results']:
        st.subheader("Comparison Results")
        exclusion_keys = get_distinct_exclusion_keys(state['results'])

        with st.container():
            if exclusion_keys:
                selected_exclusions = st.multiselect(
                    "Filter out fields:",
                    options=exclusion_keys,
                    #default=state['excluded_keys'],
                    key="file_exclusion_selector",
                    on_change=lambda: state.update({
                        'excluded_keys': set(st.session_state.file_exclusion_selector)
                    })
                )
            else:
                st.info("No fields available for filtering")

        display_results("file", selected_exclusions)

with tab2:
    st.subheader("Compare JSON from APIs")

    col1, col2 = st.columns(2)

    with col1:
        left_data = api_config_form('left', 'api')

    with col2:
        right_data = api_config_form('right', 'api')

    state = get_current_comparison_state("api")
    if state['left_data'] and state['right_data']:
        with st.container():
            st.subheader("Comparison Options")

            if is_json_list_of_objects(state['left_data']) and is_json_list_of_objects(state['right_data']):
                state['potential_join_keys'] = get_potential_join_keys(
                    state['left_data'], state['right_data']
                )
            else:
                state['potential_join_keys'] = []

            if state['potential_join_keys']:
                join_key = st.selectbox(
                    "Join Key (optional)",
                    options=[""] + state['potential_join_keys'],
                    help="Select a key to match objects in arrays",
                    key="api_join_key"
                )
            else:
                join_key = None

            if st.button("🔍 Compare API Data", use_container_width=True, key="api_compare_button"):
                with st.spinner("Comparing API data..."):
                    if (is_json_list_of_objects(state['left_data']) and
                            is_json_list_of_objects(state['right_data']) and
                            join_key):
                        state['results'] = compare_json_lists(
                            state['left_data'], state['right_data'], join_key
                        )
                    else:
                        state['results'] = compare_json_objects(
                            state['left_data'], state['right_data']
                        )

                    state['excluded_keys'] = []
                    st.success("✅ Comparison complete!")
    elif state['left_data'] or state['right_data']:
        st.warning("⚠️ Please fetch data from both APIs to compare")

    if state['results']:
        st.subheader("Comparison Results")
        exclusion_keys = get_distinct_exclusion_keys(state['results'])

        with st.container():
            if exclusion_keys:
                selected_exclusions = st.multiselect(
                    "Filter out fields:",
                    options=exclusion_keys,
                    #default= state['excluded_keys'],
                    key="api_exclusion_selector",
                    on_change=lambda: state.update({
                        'excluded_keys': set(st.session_state.api_exclusion_selector)
                    })
                )
            else:
                st.info("No fields available for filtering")

        display_results("api", selected_exclusions)

st.markdown("---")
st.caption("JSON Comparison Utility")