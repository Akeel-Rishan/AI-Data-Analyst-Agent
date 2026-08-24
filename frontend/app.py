"""Streamlit application entry point."""

import streamlit as st


st.set_page_config(
    page_title="AI Data Analyst Agent",
    page_icon="📊",
    layout="wide",
)

st.markdown(
    "<h1 style='text-align: center;'>AI Data Analyst Agent</h1>",
    unsafe_allow_html=True,
)
st.markdown(
    "<p style='text-align: center;'>Explore and understand your data with "
    "AI-assisted analysis.</p>",
    unsafe_allow_html=True,
)

st.sidebar.info("Navigation will appear here")
st.info("Welcome! Upload a dataset to begin.")
