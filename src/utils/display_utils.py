import pandas as pd
from typing import List, Dict, Set
import logging

logger = logging.getLogger(__name__)


def apply_filters(comparison_results: List[Dict], excluded_keys: List[str]) -> List[Dict]:
    """Apply current filters to comparison results"""
    excluded_set = set(excluded_keys)  # Convert to set for efficient lookups
    return [
        row for row in comparison_results
        if row['key'] not in excluded_set
    ]


def get_distinct_exclusion_keys(comparison_results: List[Dict]) -> List[str]:
    """Get distinct keys from comparison results for exclusion dropdown"""
    logger.debug("Generating distinct exclusion keys")

    if not comparison_results:
        logger.debug("No results for key extraction")
        return []

    try:
        df = pd.DataFrame(comparison_results)
        if df.empty or 'key' not in df.columns:
            logger.debug("Empty dataframe or missing 'key' column")
            return []

        keys = df['key'].unique().tolist()
        logger.debug(f"Found {len(keys)} raw keys")

        clean_keys = [k for k in keys if not any(
            part.startswith('[') and part.endswith(']')
            for part in k.split('.') if part
        )]
        logger.debug(f"Cleaned keys count: {len(clean_keys)}")

        meaningful_keys = [k for k in clean_keys if not k.startswith('[')]
        logger.debug(f"Final meaningful keys count: {len(meaningful_keys)}")

        return sorted(meaningful_keys)

    except Exception as e:
        logger.error(f"Error generating exclusion keys: {str(e)}")
        return []


def highlight_diff(row):
    """Style function for DataFrame highlighting"""
    styles = [''] * len(row)
    if row['status'] == 'different':
        styles = ['background-color: #fff3cd'] * len(row)
    elif row['status'] == 'left_only':
        styles = ['background-color: #f8d7da'] * len(row)
    elif row['status'] == 'right_only':
        styles = ['background-color: #d1e7dd'] * len(row)
    return styles