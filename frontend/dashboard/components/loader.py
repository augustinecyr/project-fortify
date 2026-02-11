# frontend/dashboard/components/loader.py
import streamlit as st

def spinner(text="Loading..."):
    """
    Context manager for a custom CSS spinner.
    Usage: with spinner("Fetching data..."): your_api_call()
    """
    css = """
    <style>
        .custom-spinner-container {
            display: flex;
            align-items: center;
            gap: 12px;
            padding: 0.75rem 0;
            font-family: -apple-system, BlinkMacSystemFont, sans-serif;
            color: #1e293b;
        }
        .custom-spinner {
            border: 3px solid #e2e8f0;
            border-top: 3px solid #1f77b4;
            border-radius: 50%;
            width: 20px;
            height: 20px;
            animation: custom-spin 1s linear infinite;
        }
        @keyframes custom-spin {
            0% { transform: rotate(0deg); }
            100% { transform: rotate(360deg); }
        }
    </style>
    """
    st.markdown(css, unsafe_allow_html=True)
    
    placeholder = st.empty()
    placeholder.markdown(
        f'<div class="custom-spinner-container">'
        f'<div class="custom-spinner"></div>'
        f'<span>{text}</span>'
        f'</div>',
        unsafe_allow_html=True
    )
    
    class SpinnerContext:
        def __enter__(self):
            return self
        def __exit__(self, exc_type, exc_val, exc_tb):
            placeholder.empty()
    
    return SpinnerContext()