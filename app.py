"""Streamlit web application for UK Broadband Price Comparison Tool."""
# --- Playwright bootstrap (portable + Cloud-safe) ---
import os, sys, subprocess
from pathlib import Path

# Use a writable cache; works locally and on Streamlit Cloud
os.environ.setdefault("XDG_CACHE_HOME", str(Path.home() / ".cache"))
os.environ.setdefault("PLAYWRIGHT_BROWSERS_PATH", str(Path.home() / ".cache" / "ms-playwright"))

def _chrome_exists(cache: Path) -> bool:
    patterns = [
        "**/chrome-linux/chrome",
        "**/chrome-win/chrome.exe",
        "**/chrome-mac/Chromium.app/Contents/MacOS/Chromium",
    ]
    for pat in patterns:
        if any(cache.glob(pat)):
            return True
    return False

def ensure_playwright_chromium():
    cache = Path(os.environ["PLAYWRIGHT_BROWSERS_PATH"])
    cache.mkdir(parents=True, exist_ok=True)

    if _chrome_exists(cache):
        return  # already installed

    # Install only Chromium; DO NOT use --with-deps on Streamlit Cloud
    try:
        subprocess.run(
            [sys.executable, "-m", "playwright", "install", "chromium"],
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            env={**os.environ},
        )
    except subprocess.CalledProcessError as e:
        # Don’t crash the app; log and let later code surface a clearer error if needed
        print("[playwright-install] failed\n", e.stdout or e)

ensure_playwright_chromium()
--------------------------------------------

import streamlit as st
import asyncio
import pandas as pd
from pathlib import Path
from datetime import datetime
import sys
from concurrent.futures import ThreadPoolExecutor
import sys

# if sys.platform.startswith("win"):
#     asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
# Add src to path
sys.path.insert(0, str(Path(__file__).parent))
# def install_playwright_browsers():
#     if not os.path.exists('/root/.cache/ms-playwright'):  # Check the path where browsers are cached
#         subprocess.run(['playwright', 'install'], check=True)
 
# Run the installation process when the app starts
# install_playwright_browsers()

from src.orchestrator import Orchestrator
from src.utils.logger import setup_logger

logger = setup_logger(__name__)

# Page configuration
st.set_page_config(
    page_title="UK Broadband Price Comparison",
    page_icon="🌐",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        font-weight: bold;
        color: #1f77b4;
        text-align: center;
        padding: 1rem 0;
    }
    .stButton>button {
        width: 100%;
    }
</style>
""", unsafe_allow_html=True)

# Header
st.markdown('<p class="main-header">🌐 UK Broadband Price Comparison Tool</p>', unsafe_allow_html=True)
st.markdown("---")

# Initialize session state
if 'results' not in st.session_state:
    st.session_state.results = None
if 'running' not in st.session_state:
    st.session_state.running = False

# Sidebar
with st.sidebar:
    st.header("⚙️ Configuration")
    
    postcode = st.text_input("Postcode *", placeholder="e.g., SW1A 1AA", help="Enter a valid UK postcode").strip().upper()
    
    st.subheader("Providers")
    all_providers = st.checkbox("All Providers", value=True)
    
    if not all_providers:
        providers = st.multiselect(
            "Select providers:",
            options=["sky", "bt", "ee", "hyperoptic", "virgin_media", "vodafone"],
            default=["sky", "bt", "ee"]
        )
    else:
        providers = ["all"]
    
    address = st.text_input("Specific Address (Optional)", placeholder="Leave empty for first available")
    
    with st.expander("🔧 Advanced Options"):
        output_format = st.selectbox("Output Format", options=["csv", "excel", "json", "all"], index=0)
        headless = st.checkbox("Headless Browser", value=True, help="Run browser in background")
        concurrent = st.checkbox("Concurrent Scraping", value=False, help="Scrape multiple providers simultaneously")
    
    st.markdown("---")
    run_button = st.button("🚀 Start Comparison", type="primary", disabled=st.session_state.running or not postcode)
    
    if st.session_state.results is not None:
        if st.button("🗑️ Clear Results"):
            st.session_state.results = None
            st.rerun()

# Main content
if not postcode and not st.session_state.running:
    st.info("👈 Please enter a postcode in the sidebar to get started")
    
    with st.expander("ℹ️ How to use"):
        st.markdown("""
        1. **Enter a postcode** in the sidebar (e.g., SW1A 1AA)
        2. **Select providers** you want to compare (or choose "All")
        3. **Click "Start Comparison"** to begin scraping
        4. **View and download results** once complete
        
        The tool will automatically visit provider websites and extract available deals.
        """)

# Run scraper
# async def run_scraper(postcode, providers, address, output_format, headless, concurrent):
#     """Run the orchestrator asynchronously."""
#     output_dir = "output"
#     Path(output_dir).mkdir(parents=True, exist_ok=True)
    
#     orchestrator = Orchestrator(
#         postcode=postcode,
#         providers=providers,
#         address=address,
#         output_format=output_format,
#         output_dir=output_dir,
#         headless=headless,
#         concurrent=concurrent
#     )
    
#     return await orchestrator.run()

from concurrent.futures import ThreadPoolExecutor
import sys
import asyncio

def run_scraper_sync(postcode, providers, address, output_format, headless, concurrent):
    async def _runner():
        orch = Orchestrator(
            postcode=postcode,
            providers=providers,
            address=address,
            output_format=output_format,
            output_dir="output",
            headless=headless,
            concurrent=concurrent,
        )
        return await orch.run()

    def _thread_entry():
        if sys.platform.startswith("win"):
            asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
        return asyncio.run(_runner())

    with ThreadPoolExecutor(max_workers=1) as ex:
        return ex.submit(_thread_entry).result()


if run_button:
    st.session_state.running = True
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    try:
        status_text.text("🔍 Initializing scrapers...")
        progress_bar.progress(10)
        
        status_text.text(f"🌐 Scraping broadband deals for {postcode}...")
        progress_bar.progress(30)
        
        # results = asyncio.run(run_scraper(
        #     postcode=postcode,
        #     providers=providers,
        #     address=address if address else None,
        #     output_format=output_format,
        #     headless=headless,
        #     concurrent=concurrent
        # ))

        results = run_scraper_sync(
            postcode=postcode,
            providers=providers,
            address=address if address else None,
            output_format=output_format,
            headless=headless,
            concurrent=concurrent
        )
        
        progress_bar.progress(90)
        status_text.text("📊 Processing results...")
        
        if results:
            st.session_state.results = results
            progress_bar.progress(100)
            status_text.empty()
            progress_bar.empty()
            st.success(f"✅ Successfully found {len(results)} deals!")
            st.rerun()
        else:
            st.session_state.running = False
            progress_bar.empty()
            status_text.empty()
            st.error("❌ No results found. Please check the postcode and try again.")
            
    except Exception as e:
        st.session_state.running = False
        progress_bar.empty()
        status_text.empty()
        st.error(f"❌ Error: {str(e)}")
        logger.error(f"Scraping error: {str(e)}", exc_info=True)

# Display results
if st.session_state.results:
    st.markdown("---")
    st.header("📊 Comparison Results")
    
    df = pd.DataFrame(st.session_state.results)
    
    # Check if we have valid data
    if df.empty:
        st.warning("No valid deals found. Please try a different postcode or check the logs.")
    else:
        # Summary metrics
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Total Deals", len(df))
        with col2:
            provider_col = 'provider' if 'provider' in df.columns else 'Provider' if 'Provider' in df.columns else None
            if provider_col:
                st.metric("Providers", df[provider_col].nunique())
            else:
                st.metric("Providers", "N/A")
        with col3:
            try:
                price_col = next((col for col in df.columns if 'price' in col.lower()), None)
                if price_col:
                    avg_price = pd.to_numeric(df[price_col], errors='coerce').mean()
                    st.metric("Avg Monthly Price", f"£{avg_price:.2f}" if not pd.isna(avg_price) else "N/A")
                else:
                    st.metric("Avg Monthly Price", "N/A")
            except:
                st.metric("Avg Monthly Price", "N/A")
        with col4:
            try:
                speed_col = next((col for col in df.columns if 'download' in col.lower() and 'speed' in col.lower()), None)
                if speed_col:
                    max_speed = pd.to_numeric(df[speed_col], errors='coerce').max()
                    st.metric("Max Speed", f"{int(max_speed)} Mbps" if not pd.isna(max_speed) else "N/A")
                else:
                    st.metric("Max Speed", "N/A")
            except:
                st.metric("Max Speed", "N/A")
    
        st.markdown("---")
        
        # Filters
        provider_col = 'provider' if 'provider' in df.columns else 'Provider' if 'Provider' in df.columns else None
        
        if provider_col:
            col1, col2 = st.columns(2)
            with col1:
                selected_providers = st.multiselect(
                    "Filter by Provider:",
                    options=df[provider_col].unique(),
                    default=df[provider_col].unique()
                )
            with col2:
                package_col = next((col for col in df.columns if col.lower() in ['package', 'deal_name']), None)
                if package_col:
                    selected_packages = st.multiselect(
                        "Filter by Package Type:",
                        options=df[package_col].unique(),
                        default=df[package_col].unique()
                    )
                else:
                    selected_packages = None
            
            # Apply filters
            if selected_packages:
                filtered_df = df[
                    (df[provider_col].isin(selected_providers)) &
                    (df[package_col].isin(selected_packages))
                ]
            else:
                filtered_df = df[df[provider_col].isin(selected_providers)]
        else:
            filtered_df = df
        
        # Display table
        st.dataframe(filtered_df, use_container_width=True, hide_index=True)
        
        # Download buttons
        st.markdown("---")
        st.subheader("📥 Download Results")
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            csv = filtered_df.to_csv(index=False)
            st.download_button(
                label="📄 Download CSV",
                data=csv,
                file_name=f"broadband_comparison_{postcode}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                mime="text/csv"
            )
        
        with col2:
            try:
                from io import BytesIO
                buffer = BytesIO()
                with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
                    filtered_df.to_excel(writer, index=False, sheet_name='Results')
                buffer.seek(0)
                
                st.download_button(
                    label="📊 Download Excel",
                    data=buffer,
                    file_name=f"broadband_comparison_{postcode}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )
            except ImportError:
                st.info("Install openpyxl to enable Excel export")
        
        with col3:
            json_data = filtered_df.to_json(orient='records', indent=2)
            st.download_button(
                label="📋 Download JSON",
                data=json_data,
                file_name=f"broadband_comparison_{postcode}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
                mime="application/json"
            )

# Footer
st.markdown("---")
st.markdown(
    """
    <div style='text-align: center; color: gray; font-size: 0.8rem;'>
    UK Broadband Price Comparison Tool v1.0.0
    </div>
    """,
    unsafe_allow_html=True
)


