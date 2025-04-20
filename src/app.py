import streamlit as st
import pandas as pd
import json
from utils.json_comparison import (
    compare_json_objects,
    compare_json_lists,
    is_json_list_of_objects,
    get_all_keys,
    get_potential_join_keys
)
from utils.api_utils import APIHandler
from utils.state_utils import init_session_state, get_current_comparison_state
from utils.display_utils import get_distinct_exclusion_keys, apply_filters, highlight_diff
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


def get_flattened_keys(json_data, parent_key=''):
    """Recursively extract all keys from nested dicts/lists, flattening them (e.g., address.city)."""
    keys = set()
    if isinstance(json_data, dict):
        for k, v in json_data.items():
            full_key = f"{parent_key}.{k}" if parent_key else k
            if isinstance(v, dict):
                keys |= get_flattened_keys(v, full_key)
            elif isinstance(v, list) and v and isinstance(v[0], dict):
                # Only sample the first element of the list
                keys |= get_flattened_keys(v[0], full_key)
            else:
                keys.add(full_key)
    elif isinstance(json_data, list) and json_data and isinstance(json_data[0], dict):
        keys |= get_flattened_keys(json_data[0], parent_key)
    return keys


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


def review_and_exclude_keys(json_data):
    """Allow users to review and exclude keys before comparison (flattened keys, including nested)."""
    all_keys = get_flattened_keys(json_data)
    suggested_exclusions = [key for key in all_keys if any(ts in key.lower() for ts in ['timestamp', 'created_at', 'updated_at', 'run_id'])]
    with st.expander("🔍 Review and Exclude Keys", expanded=True):
        st.markdown("**Suggested Exclusions:**")
        st.write(suggested_exclusions)
        selected_exclusions = st.multiselect(
            "Select keys to exclude (including nested):",
            options=sorted(list(all_keys)),
            default=suggested_exclusions,
            key="review_exclusion_selector"
        )
    return set(selected_exclusions)


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
tab1, tab2, tab3 = st.tabs(["📁 File Comparison", "🌐 API Comparison", "📝 JSON Formatter"])

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
            state['all_keys'] = get_flattened_keys(left_json) | get_flattened_keys(right_json)

            # Allow users to review and exclude keys before comparison
            state['excluded_keys'] = review_and_exclude_keys(left_json)

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

                    st.success("✅ Comparison complete!")

    elif left_file or right_file:
        st.warning("⚠️ Please upload both files to compare")

    if state['results']:
        st.subheader("Comparison Results")

        with st.container():
            st.markdown("**Apply Filters:**")
            exclusion_keys = sorted(get_flattened_keys(left_json) | get_flattened_keys(right_json))

            if exclusion_keys:
                selected_exclusions = st.multiselect(
                    "Filter out fields (including nested):",
                    options=exclusion_keys,
                    default=list(state['excluded_keys']),
                    key="file_exclusion_selector"
                )

                if st.button("Apply Filters", key="apply_filters_button"):
                    state['excluded_keys'] = set(selected_exclusions)
                    display_results("file", list(state['excluded_keys']))
            else:
                st.info("No fields available for filtering")

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

with tab3:
    st.subheader("JSON Formatter & Playground")
    st.markdown("""
    <style>
    .json-formatter-header {
        font-size: 1.2rem;
        font-weight: 600;
        margin-bottom: 0.5em;
    }
    .json-formatter-actions {
        margin-bottom: 1em;
    }
    .json-formatter-success {
        color: #198754;
        font-weight: 500;
    }
    .json-formatter-error {
        color: #dc3545;
        font-weight: 500;
    }
    .json-formatter-area {
        min-height: 400px;
        height: 100%;
        resize: vertical;
        font-family: monospace;
        font-size: 1rem;
    }
    </style>
    """, unsafe_allow_html=True)
    col1, col2 = st.columns(2, gap="large")
    with col1:
        st.markdown("**Input JSON**")
        json_text = st.text_area("Paste or edit your JSON here:", height=400, key="json_formatter_input",
                                placeholder='Paste or type your JSON here...',
                                help="Paste any JSON to format, minify, validate, and copy.")
        format_btn, minify_btn = st.columns(2)
        format_clicked = format_btn.button("Format", key="format_json_btn")
        minify_clicked = minify_btn.button("Minify", key="minify_json_btn")
    with col2:
        st.markdown("**Output & Actions**")
        output_json = None
        error_msg = None
        if format_clicked or minify_clicked:
            try:
                parsed_json = json.loads(json_text)
                if format_clicked:
                    output_json = json.dumps(parsed_json, indent=2, ensure_ascii=False)
                    st.markdown('<span class="json-formatter-success">Valid JSON! Expand/collapse below:</span>', unsafe_allow_html=True)
                    st.json(parsed_json, expanded=True)
                    st.markdown('<div class="json-formatter-actions">', unsafe_allow_html=True)
                    st.code(output_json, language="json")
                    st.button("Copy Output JSON", key="copy_output_json_btn", on_click=lambda: st.session_state.update({"copied_json": output_json}))
                    st.markdown('</div>', unsafe_allow_html=True)
                elif minify_clicked:
                    output_json = json.dumps(parsed_json, separators=(',', ':'), ensure_ascii=False)
                    st.markdown('<span class="json-formatter-success">Minified JSON below:</span>', unsafe_allow_html=True)
                    st.code(output_json, language="json")
                    st.button("Copy Output JSON", key="copy_output_json_btn_minify", on_click=lambda: st.session_state.update({"copied_json": output_json}))
            except Exception as e:
                error_msg = f"Invalid JSON: {e}"
                st.markdown(f'<span class="json-formatter-error">{error_msg}</span>', unsafe_allow_html=True)
        if error_msg:
            st.info("Tip: Use the Format button for pretty JSON or Minify for compact JSON.")
        # Show a copy success toast if copied
        if st.session_state.get("copied_json"):
            st.toast("Copied to clipboard! (Use ⌘+C or Ctrl+C to copy from the code box)")
            st.session_state["copied_json"] = None
        st.markdown("""
        <ul>
          <li>🔍 <b>Format</b> for pretty, indented JSON</li>
          <li>⚡ <b>Minify</b> for compact JSON (great for APIs)</li>
          <li>📋 <b>Copy</b> output JSON with one click</li>
          <li>🧩 <b>Expand/collapse</b> JSON structure interactively (when formatted)</li>
          <li>💡 <b>Instant validation</b> and error feedback</li>
        </ul>
        """, unsafe_allow_html=True)

st.markdown("---")
st.caption("JSON Comparison Utility")