import os
import requests
import argparse
from bs4 import BeautifulSoup
from urllib.parse import urlparse
from newspaper import Article
from nltk.tokenize import sent_tokenize
import nltk
import json
import time
from serpapi import GoogleSearch
from dotenv import load_dotenv

# Load environment variables from .env file if present
load_dotenv()

# Download necessary NLTK data
try:
    nltk.data.find('tokenizers/punkt')
except LookupError:
    nltk.download('punkt')

class WebScraperAI:
    def __init__(self):
        # Load API keys from environment variables or use defaults
        self.serpapi_key = os.environ.get("SERPAPI_KEY", "")
        self.hf_api_key = os.environ.get("HUGGINGFACE_KEY", "")
        self.search_results = []
        self.content = {}
        self.summaries = {}
        self.failed_urls = []  # Initialize empty list of failed URLs
    
    def clear_data_folder(self):
        """Delete all existing files in the data folder before adding new content"""
        data_dir = "data"
        if os.path.exists(data_dir):
            for filename in os.listdir(data_dir):
                file_path = os.path.join(data_dir, filename)
                try:
                    if os.path.isfile(file_path):
                        os.unlink(file_path)
                except Exception as e:
                    print(f"Failed to delete {file_path}: {e}")

    def set_serpapi_key(self, key):
        """Set SerpAPI key - for testing or CLI usage only"""
        self.serpapi_key = key
    
    def set_hf_api_key(self, key):
        """Set HuggingFace API key - for testing or CLI usage only"""
        self.hf_api_key = key
    
    # def get_failed_urls(self):
    #     """Return the list of URLs that failed to scrape"""
    #     return self.failed_urls
    
    def search_web(self, query, num_results=5):
        """Search the web using SerpAPI (Google Search)"""
        if not self.serpapi_key:
            raise ValueError("SerpAPI key is not set. Please set it using environment variable SERPAPI_KEY.")
            
        params = {
            "q": query,
            "api_key": self.serpapi_key,
            "num": num_results
        }
        
        try:
            search = GoogleSearch(params)
            results = search.get_dict()
            
            if "organic_results" in results:
                self.search_results = [result["link"] for result in results["organic_results"][:num_results]]
                return self.search_results
            else:
                print("No search results found.")
                return []
        except Exception as e:
            print(f"Error searching web: {e}")
            return []
    
    def scrape_website(self, url):
        """Scrape content from a website using newspaper3k"""
        try:
            article = Article(url)
            article.download()
            article.parse()
            
            # Check if content was actually found
            if not article.text or len(article.text.strip()) < 50:
                print(f"No significant content found on {url}")
                self.failed_urls.append(url)
                return None
            
            # Store content with metadata
            self.content[url] = {
                "title": article.title,
                "text": article.text,
                "publish_date": str(article.publish_date) if article.publish_date else None,
                "authors": article.authors,
                "top_image": article.top_image,
                "source_url": url  # Store original source URL to track provenance
            }
            
            return self.content[url]
        except Exception as e:
            print(f"Error scraping {url}: {e}")
            self.failed_urls.append(url)
            return None
    
    def batch_scrape(self, urls):
        """Scrape content from multiple websites"""
        results = []
        self.failed_urls = []  # Reset failed URLs list
        
        for url in urls:
            print(f"Scraping: {url}")
            result = self.scrape_website(url)
            if result:
                results.append((url, result))
        
        return results

    def summarize_text(self, text, max_length=500):
        """Summarize text using HuggingFace API (free tier)"""
        if not self.hf_api_key:
            return self._simple_summarize(text)
            
        API_URL = "https://api-inference.huggingface.co/models/facebook/bart-large-cnn"
        headers = {"Authorization": f"Bearer {self.hf_api_key}"}
        
        # Truncate long text to fit the model's input limits
        if len(text) > 5000:
            text = text[:5000]
        
        payload = {
            "inputs": text,
            "parameters": {
                "max_length": max_length,
                "min_length": 100,
            }
        }
        
        try:
            response = requests.post(API_URL, headers=headers, json=payload)
            if response.status_code == 200:
                return response.json()[0]["summary_text"]
            else:
                print(f"Error from HuggingFace API: {response.text}")
                # Fallback to simple extractive summarization
                return self._simple_summarize(text)
        except Exception as e:
            print(f"Error summarizing text: {e}")
            return self._simple_summarize(text)
    
    def _simple_summarize(self, text, num_sentences=5):
        """Simple extractive summarization as fallback"""
        sentences = sent_tokenize(text)
        return " ".join(sentences[:num_sentences])
    
    def analyze_and_summarize(self):
        """Analyze and summarize all scraped content"""
        all_text = ""
        
        for url, data in self.content.items():
            print(f"Summarizing: {url}")
            text = data["text"]
            summary = self.summarize_text(text)
            self.summaries[url] = summary
            all_text += f"{data['title']}\n{text}\n\n"
        
        # Create an overall summary only if we have content
        if all_text:
            overall_summary = self.summarize_text(all_text, max_length=1000)
            self.summaries["overall"] = overall_summary
        
        return self.summaries
    
    def save_results(self, filename="scraper_results.json"):
        """Save all results to a JSON file"""
        results = {
            "search_results": self.search_results,
            "content": self.content,
            "summaries": self.summaries,
            "failed_urls": self.failed_urls
        }
        
        with open(filename, "w", encoding="utf-8") as f:
            json.dump(results, f, indent=2, ensure_ascii=False)
        
        print(f"Results saved to {filename}")
        return filename
    
    def suggest_alternative_resources(self, failed_url, query=None):
        """Suggest alternative resources for failed URLs"""
        if not query:
            # Extract domain name from the failed URL to use as a query
            parsed_url = urlparse(failed_url)
            domain = parsed_url.netloc
            query = f"site:{domain} information"
        
        try:
            return self.search_web(query, 3)
        except:
            return []