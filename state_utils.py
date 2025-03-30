import logging
from typing import Dict, Any, List, Optional
import streamlit as st

def init_session_state():
    """Initialize all session state variables"""
    if 'file_comparison' not in st.session_state:
        st.session_state.file_comparison = {
            'results': None,
            'excluded_keys': [],  # Changed from set to list
            'all_keys': set(),
            'potential_join_keys': []
        }

    if 'api_comparison' not in st.session_state:
        st.session_state.api_comparison = {
            'results': None,
            'excluded_keys': [],  # Changed from set to list
            'all_keys': set(),
            'potential_join_keys': [],
            'left_data': None,
            'right_data': None
        }

def get_current_comparison_state(tab_name: str) -> Dict[str, Any]:
    """Get the state dictionary for the current tab"""
    state = st.session_state.file_comparison if tab_name == "file" else st.session_state.api_comparison
    logging.info(f"state for {tab_name} : {state}")
    return state

def reset_comparison_state(tab_name: str):
    """Reset the comparison state for a specific tab"""
    if tab_name == "file":
        st.session_state.file_comparison = {
            'results': None,
            'excluded_keys': [],
            'all_keys': set(),
            'potential_join_keys': []
        }
    else:
        st.session_state.api_comparison = {
            'results': None,
            'excluded_keys': [],
            'all_keys': set(),
            'potential_join_keys': [],
            'left_data': None,
            'right_data': None
        }