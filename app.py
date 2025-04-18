import streamlit as st
from backend import WebScraperAI
import pandas as pd
import os

st.set_page_config(page_title="AI Web Scraper", layout="wide")
st.title("🌐 AI-Powered Web Scraper Agent")

# Initialize the scraper
@st.cache_resource
def get_scraper():
    return WebScraperAI()

scraper = get_scraper()

# Setup tab
with st.sidebar:
    st.header("Settings")
    
    # Only show API key fields if environment variables are not set
    if not os.environ.get("SERPAPI_KEY"):
        serpapi_key = st.text_input("SerpAPI Key:", type="password", 
                                     help="Get free key from https://serpapi.com/")
        if serpapi_key:
            scraper.set_serpapi_key(serpapi_key)
    else:
        st.success("✅ SerpAPI key configured in backend")
        
    if not os.environ.get("HUGGINGFACE_KEY"):
        hf_api_key = st.text_input("HuggingFace API Key:", type="password", 
                                   help="Get free key from https://huggingface.co/settings/tokens")
        if hf_api_key:
            scraper.set_hf_api_key(hf_api_key)
    else:
        st.success("✅ HuggingFace key configured in backend")

# Main interface
tab1, tab2, tab3 = st.tabs(["Search & Scrape", "Results", "Failed URLs"])

with tab1:
    st.header("Search & Scrape")
    
    # Search query input
    col1, col2 = st.columns([3, 1])
    with col1:
        query = st.text_input("Enter search query:", placeholder="e.g., latest AI research")
    with col2:
        num_results = st.number_input("Number of results:", min_value=1, max_value=20, value=5)
    
    # Direct URL input
    st.subheader("Or enter specific URLs:")
    urls_input = st.text_area("Enter URLs (one per line):", height=100)
    
    # Action buttons
    if st.button("Search & Scrape"):
        # Check if API keys are available
        if (not os.environ.get("SERPAPI_KEY") and not scraper.serpapi_key) and query:
            st.error("SerpAPI key is required for searching. Please add it in the sidebar or set the SERPAPI_KEY environment variable.")
        elif query:
            try:
                with st.spinner("Searching..."):
                    urls = scraper.search_web(query, num_results)
                    if urls:
                        st.success(f"Found {len(urls)} URLs")
                        st.session_state.urls = urls
                        st.session_state.search_query = query
                    else:
                        st.error("No results found. Try a different query.")
            except ValueError as e:
                st.error(str(e))
        elif urls_input:
            urls = [url.strip() for url in urls_input.split("\n") if url.strip()]
            st.session_state.urls = urls
            st.session_state.search_query = None
            st.success(f"Processing {len(urls)} URLs")
        else:
            st.warning("Please provide either a search query or URLs to scrape.")
            
        # Scrape the websites
        if 'urls' in st.session_state and st.session_state.urls:
            with st.spinner("Scraping websites..."):
                results = scraper.batch_scrape(st.session_state.urls)
                # failed_urls = scraper.get_failed_urls()
                
                if results:
                    st.success(f"Successfully scraped {len(results)} websites")
                    st.session_state.scraped = True
                    # st.session_state.failed_urls = failed_urls
                    
                #     if failed_urls:
                #         st.warning(f"Failed to scrape {len(failed_urls)} URLs. See the 'Failed URLs' tab for details.")
                # else:
                #     st.error("Failed to scrape any websites. Check the URLs or try again.")
                #     if failed_urls:
                #         st.session_state.failed_urls = failed_urls
                #         st.info("See the 'Failed URLs' tab for options.")
                    
            # Analyze and summarize successful scrapes
            if hasattr(st.session_state, 'scraped') and st.session_state.scraped:
                with st.spinner("Analyzing and summarizing content..."):
                    summaries = scraper.analyze_and_summarize()
                    if summaries:
                        st.session_state.summaries = summaries
                        st.success("Analysis complete!")
                        st.session_state.filename = scraper.save_results()
                        st.balloons()
                    else:
                        st.warning("No content to analyze.")

with tab2:
    st.header("Results")
    
    if hasattr(st.session_state, 'summaries') and st.session_state.summaries:
        # Overall summary
        if "overall" in st.session_state.summaries:
            st.subheader("Overall Summary")
            st.write(st.session_state.summaries["overall"])
        
        # Individual page summaries
        st.subheader("Page Summaries")
        for url in scraper.content:
            with st.expander(f"{scraper.content[url]['title'] or url}"):
                if url in st.session_state.summaries:
                    st.markdown("### Summary")
                    st.write(st.session_state.summaries[url])
                
                st.markdown("### Content Details")
                col1, col2 = st.columns(2)
                with col1:
                    st.markdown(f"**URL:** [{url}]({url})")
                    st.markdown(f"**Authors:** {', '.join(scraper.content[url]['authors']) if scraper.content[url]['authors'] else 'Unknown'}")
                with col2:
                    st.markdown(f"**Publish Date:** {scraper.content[url]['publish_date'] or 'Unknown'}")
                
                if scraper.content[url]['top_image']:
                    st.image(scraper.content[url]['top_image'], width=300)
        
        # Download results
        if hasattr(st.session_state, 'filename'):
            with open(st.session_state.filename, "r", encoding="utf-8") as f:
                st.download_button(
                    label="Download Results as JSON",
                    data=f,
                    file_name=st.session_state.filename,
                    mime="application/json"
                )
    else:
        st.info("No results yet. Go to the 'Search & Scrape' tab to get started.")

with tab3:
    st.header("Failed URLs")
    
    if hasattr(st.session_state, 'failed_urls') and st.session_state.failed_urls:
        st.write(f"The following URLs could not be scraped successfully:")
        
        for i, url in enumerate(st.session_state.failed_urls):
            with st.container():
                st.markdown(f"### {i+1}. [{url}]({url})")
                
                col1, col2 = st.columns([3, 1])
                with col1:
                    st.write("No content could be extracted from this URL.")
                with col2:
                    key = f"find_alternatives_{i}"
                    if st.button("Find Alternative Resources", key=key):
                        with st.spinner("Searching for alternatives..."):
                            alternatives = scraper.suggest_alternative_resources(
                                url, 
                                st.session_state.get('search_query', None)
                            )
                            if alternatives:
                                st.success("Found alternative resources:")
                                for alt_url in alternatives:
                                    st.markdown(f"- [{alt_url}]({alt_url})")
                                
                                # Allow adding these to the scraper
                                add_key = f"add_alternatives_{i}"
                                if st.button("Add These Resources to Scraper", key=add_key):
                                    st.session_state.urls = alternatives
                                    st.success("Added to scraper. Go back to 'Search & Scrape' tab and click 'Search & Scrape' again.")
                            else:
                                st.error("No alternative resources found.")
    else:
        st.info("No failed URLs yet. This tab will show URLs that couldn't be scraped successfully.")