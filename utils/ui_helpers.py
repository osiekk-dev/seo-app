import streamlit as st

def apply_footer():
    st.markdown("""
    <style>
    footer {visibility: hidden;}
    .custom-footer {
        position: fixed; bottom: 0; left: 0; right: 0;
        background: #0e1117; color: #555; 
        text-align: center; padding: 6px; font-size: 11px; z-index: 999;
    }
    </style>
    <div class="custom-footer">DD Serwis – SEO Content Engine</div>
    """, unsafe_allow_html=True)
