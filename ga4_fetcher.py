from google.oauth2 import service_account
from google.analytics.data_v1beta import BetaAnalyticsDataClient
from google.analytics.data_v1beta.types import DateRange, Dimension, Metric, RunReportRequest
from datetime import datetime, timedelta
import streamlit as st

class GA4Fetcher:
    def __init__(self):
        """Initialize GA4 API client with service account"""
        try:
            credentials = service_account.Credentials.from_service_account_info(
                st.secrets["gcp_service_account"],
                scopes=['https://www.googleapis.com/auth/analytics.readonly']
            )
            self.client = BetaAnalyticsDataClient(credentials=credentials)
        except Exception as e:
            st.error(f"GA4 Authentication Error: {e}")
            self.client = None
    
    def get_analytics_data(self, property_id, days=28):
        """
        Fetch analytics data from GA4
        
        Args:
            property_id: GA4 property ID (e.g., '123456789')
            days: Number of days of data to fetch
        
        Returns:
            dict with traffic data, top pages, sources
        """
        if not self.client:
            return None
        
        try:
            # Format property ID
            if not property_id.startswith('properties/'):
                property_id = f'properties/{property_id}'
            
            # Date range
            end_date = datetime.now().date()
            start_date = end_date - timedelta(days=days)
            
            # Get overall metrics
            request = RunReportRequest(
                property=property_id,
                date_ranges=[DateRange(
                    start_date=str(start_date),
                    end_date=str(end_date)
                )],
                metrics=[
                    Metric(name="sessions"),
                    Metric(name="totalUsers"),
                    Metric(name="screenPageViews"),
                    Metric(name="bounceRate"),
                    Metric(name="averageSessionDuration")
                ]
            )
            
            response = self.client.run_report(request)
            
            # Extract overall metrics
            if response.rows:
                row = response.rows[0]
                overall = {
                    'sessions': int(row.metric_values[0].value),
                    'users': int(row.metric_values[1].value),
                    'pageviews': int(row.metric_values[2].value),
                    'bounce_rate': round(float(row.metric_values[3].value) * 100, 2),
                    'avg_session_duration': round(float(row.metric_values[4].value), 2)
                }
            else:
                overall = None
            
            # Get top pages
            request_pages = RunReportRequest(
                property=property_id,
                date_ranges=[DateRange(
                    start_date=str(start_date),
                    end_date=str(end_date)
                )],
                dimensions=[Dimension(name="pagePath")],
                metrics=[
                    Metric(name="screenPageViews"),
                    Metric(name="sessions")
                ],
                limit=10
            )
            
            response_pages = self.client.run_report(request_pages)
            
            top_pages = []
            for row in response_pages.rows:
                top_pages.append({
                    'page': row.dimension_values[0].value,
                    'pageviews': int(row.metric_values[0].value),
                    'sessions': int(row.metric_values[1].value)
                })
            
            # Get traffic sources
            request_sources = RunReportRequest(
                property=property_id,
                date_ranges=[DateRange(
                    start_date=str(start_date),
                    end_date=str(end_date)
                )],
                dimensions=[Dimension(name="sessionSource")],
                metrics=[Metric(name="sessions")],
                limit=10
            )
            
            response_sources = self.client.run_report(request_sources)
            
            traffic_sources = []
            for row in response_sources.rows:
                traffic_sources.append({
                    'source': row.dimension_values[0].value,
                    'sessions': int(row.metric_values[0].value)
                })
            
            return {
                'success': True,
                'overall': overall,
                'top_pages': top_pages,
                'traffic_sources': traffic_sources,
                'date_range': f"{start_date} to {end_date}"
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'message': 'Could not fetch GA4 data. Please ensure the service account email has been added as a Viewer in GA4 property settings.'
            }