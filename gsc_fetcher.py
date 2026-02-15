from google.oauth2 import service_account
from googleapiclient.discovery import build
from datetime import datetime, timedelta
import streamlit as st

class GSCFetcher:
    def __init__(self):
        """Initialize GSC API client with service account"""
        try:
            credentials = service_account.Credentials.from_service_account_info(
                st.secrets["gcp_service_account"],
                scopes=['https://www.googleapis.com/auth/webmasters.readonly']
            )
            self.service = build('searchconsole', 'v1', credentials=credentials)
        except Exception as e:
            st.error(f"GSC Authentication Error: {e}")
            self.service = None
    
    def get_search_analytics(self, site_url, days=28):
        """
        Fetch search analytics data from GSC
        
        Args:
            site_url: GSC property URL (e.g., 'https://example.com' or 'sc-domain:example.com')
            days: Number of days of data to fetch (default 28)
        
        Returns:
            dict with queries, pages, and summary data
        """
        if not self.service:
            return None
        
        try:
            # Date range
            end_date = datetime.now().date()
            start_date = end_date - timedelta(days=days)
            
            # Request body
            request_body = {
                'startDate': str(start_date),
                'endDate': str(end_date),
                'dimensions': ['query'],
                'rowLimit': 25,
                'startRow': 0
            }
            
            # Fetch top queries
            response = self.service.searchanalytics().query(
                siteUrl=site_url,
                body=request_body
            ).execute()
            
            queries = response.get('rows', [])
            
            # Fetch top pages
            request_body['dimensions'] = ['page']
            response_pages = self.service.searchanalytics().query(
                siteUrl=site_url,
                body=request_body
            ).execute()
            
            pages = response_pages.get('rows', [])
            
            # Calculate totals
            total_clicks = sum([q.get('clicks', 0) for q in queries])
            total_impressions = sum([q.get('impressions', 0) for q in queries])
            avg_ctr = (total_clicks / total_impressions * 100) if total_impressions > 0 else 0
            avg_position = sum([q.get('position', 0) for q in queries]) / len(queries) if queries else 0
            
            return {
                'success': True,
                'queries': queries,
                'pages': pages,
                'summary': {
                    'total_clicks': total_clicks,
                    'total_impressions': total_impressions,
                    'avg_ctr': round(avg_ctr, 2),
                    'avg_position': round(avg_position, 1),
                    'date_range': f"{start_date} to {end_date}"
                }
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'message': 'Could not fetch GSC data. Please ensure the service account email has been added as a user in Google Search Console.'
            }
    
    def test_access(self, site_url):
        """Test if we have access to the GSC property"""
        try:
            self.service.sites().get(siteUrl=site_url).execute()
            return True
        except:
            return False