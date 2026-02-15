from xhtml2pdf import pisa
from datetime import datetime
import os
import tempfile

class PDFGenerator:
    def __init__(self):
        """Initialize PDF generator"""
        pass
    
    def generate_audit_pdf(self, client_data, pages_data, technical_findings, has_blog, gsc_data, ga4_data, recommendations):
        """
        Generate comprehensive SEO audit PDF
        
        Args:
            client_data: dict with name, email, company, website
            pages_data: list of page analysis results
            technical_findings: dict with technical SEO findings
            has_blog: boolean
            gsc_data: GSC analytics data (or None)
            ga4_data: GA4 analytics data (or None)
            recommendations: AI-generated recommendations text
        
        Returns:
            Path to generated PDF file
        """
        
        # Calculate overall score
        overall_score = self._calculate_seo_score(pages_data, technical_findings, gsc_data, ga4_data)
        
        # Generate HTML
        html_content = self._generate_html(
            client_data, pages_data, technical_findings, has_blog, 
            gsc_data, ga4_data, recommendations, overall_score
        )
        
        # Generate PDF
        pdf_path = self._html_to_pdf(html_content, client_data['website'])
        
        return pdf_path
    
    def _calculate_seo_score(self, pages_data, technical_findings, gsc_data, ga4_data):
        """Calculate overall SEO score out of 100"""
        score = 0
        max_score = 100
        
        # Technical infrastructure (20 points)
        if technical_findings.get('has_robots_txt'):
            score += 5
        if technical_findings.get('has_sitemap'):
            score += 5
        
        # Page optimization (30 points)
        if pages_data:
            homepage = pages_data[0]
            
            # Title optimization (10 points)
            if 50 <= homepage['title_length'] <= 60:
                score += 10
            elif 30 <= homepage['title_length'] <= 70:
                score += 5
            
            # Meta description (10 points)
            if 120 <= homepage['meta_length'] <= 160:
                score += 10
            elif 80 <= homepage['meta_length'] <= 180:
                score += 5
            
            # H1 tags (5 points)
            if homepage['h1_count'] == 1:
                score += 5
            
            # Page speed (5 points)
            if homepage['load_time'] < 2:
                score += 5
            elif homepage['load_time'] < 3:
                score += 3
        
        # Schema markup (10 points)
        if pages_data and pages_data[0]['schemas']:
            score += 10
        
        # Data connectivity (20 points)
        if gsc_data and gsc_data.get('success'):
            score += 10
        if ga4_data and ga4_data.get('success'):
            score += 10
        
        # Additional optimizations (20 points)
        if pages_data:
            homepage = pages_data[0]
            elements = homepage['page_elements']
            
            if elements.get('has_canonical'):
                score += 5
            if elements.get('has_opengraph'):
                score += 5
            if elements.get('has_gsc_verification'):
                score += 5
            
            # Image optimization
            resources = homepage['resources']
            if resources['total_images'] > 0:
                alt_ratio = 1 - (resources['images_without_alt'] / resources['total_images'])
                score += int(alt_ratio * 5)
        
        return min(score, max_score)
    
    def _generate_html(self, client_data, pages_data, technical_findings, has_blog, gsc_data, ga4_data, recommendations, overall_score):
        """Generate HTML content for PDF"""
        
        # Determine score color
        if overall_score >= 80:
            score_color = "#10b981"  # green
            score_label = "Excellent"
        elif overall_score >= 60:
            score_color = "#f59e0b"  # yellow
            score_label = "Good"
        elif overall_score >= 40:
            score_color = "#f97316"  # orange
            score_label = "Needs Improvement"
        else:
            score_color = "#ef4444"  # red
            score_label = "Critical Issues"
        
        # Build HTML
        html = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>SEO Audit Report - {client_data['website']}</title>
    <style>
        @page {{
            size: A4;
            margin: 2cm;
            @bottom-right {{
                content: "Page " counter(page) " of " counter(pages);
                font-size: 10px;
                color: #666;
            }}
            @bottom-left {{
                content: "Prepared by Punkaj Saini | psdigital.io";
                font-size: 10px;
                color: #666;
            }}
        }}
        
        body {{
            font-family: 'Segoe UI', Arial, sans-serif;
            line-height: 1.6;
            color: #333;
            margin: 0;
            padding: 0;
        }}
        
        .cover {{
            text-align: center;
            padding: 100px 0;
            page-break-after: always;
        }}
        
        .cover h1 {{
            font-size: 36px;
            color: #1e40af;
            margin-bottom: 20px;
        }}
        
        .cover h2 {{
            font-size: 24px;
            color: #64748b;
            margin-bottom: 40px;
        }}
        
        .cover .score {{
            font-size: 72px;
            font-weight: bold;
            color: {score_color};
            margin: 40px 0 20px 0;
        }}
        
        .cover .score-label {{
            font-size: 24px;
            color: {score_color};
            margin-bottom: 60px;
        }}
        
        .cover .meta {{
            font-size: 14px;
            color: #64748b;
            margin-top: 60px;
        }}
        
        .section {{
            page-break-before: always;
            margin-bottom: 30px;
        }}
        
        h1 {{
            color: #1e40af;
            font-size: 28px;
            border-bottom: 3px solid #1e40af;
            padding-bottom: 10px;
            margin-bottom: 20px;
        }}
        
        h2 {{
            color: #1e40af;
            font-size: 22px;
            margin-top: 30px;
            margin-bottom: 15px;
        }}
        
        h3 {{
            color: #475569;
            font-size: 18px;
            margin-top: 20px;
            margin-bottom: 10px;
        }}
        
        .metric-grid {{
            display: grid;
            grid-template-columns: repeat(3, 1fr);
            gap: 20px;
            margin: 20px 0;
        }}
        
        .metric-box {{
            border: 2px solid #e2e8f0;
            border-radius: 8px;
            padding: 15px;
            text-align: center;
        }}
        
        .metric-value {{
            font-size: 32px;
            font-weight: bold;
            color: #1e40af;
            margin-bottom: 5px;
        }}
        
        .metric-label {{
            font-size: 14px;
            color: #64748b;
        }}
        
        .status-good {{ color: #10b981; }}
        .status-warning {{ color: #f59e0b; }}
        .status-critical {{ color: #ef4444; }}
        
        table {{
            width: 100%;
            border-collapse: collapse;
            margin: 20px 0;
            font-size: 14px;
        }}
        
        th {{
            background-color: #1e40af;
            color: white;
            padding: 12px;
            text-align: left;
            font-weight: 600;
        }}
        
        td {{
            padding: 10px 12px;
            border-bottom: 1px solid #e2e8f0;
        }}
        
        tr:nth-child(even) {{
            background-color: #f8fafc;
        }}
        
        .recommendation {{
            background-color: #f0f9ff;
            border-left: 4px solid #1e40af;
            padding: 15px;
            margin: 15px 0;
        }}
        
        .recommendation h4 {{
            color: #1e40af;
            margin-top: 0;
            font-size: 16px;
        }}
        
        .priority-high {{
            border-left-color: #ef4444;
            background-color: #fef2f2;
        }}
        
        .priority-medium {{
            border-left-color: #f59e0b;
            background-color: #fffbeb;
        }}
        
        .priority-low {{
            border-left-color: #10b981;
            background-color: #f0fdf4;
        }}
        
        .info-box {{
            background-color: #f8fafc;
            border-radius: 8px;
            padding: 15px;
            margin: 15px 0;
        }}
        
        ul {{
            margin: 10px 0;
            padding-left: 25px;
        }}
        
        li {{
            margin: 8px 0;
        }}
    </style>
</head>
<body>
    <!-- Cover Page -->
    <div class="cover">
        <h1>SEO Audit Report</h1>
        <h2>{client_data['website']}</h2>
        
        <div class="score">{overall_score}</div>
        <div class="score-label">{score_label}</div>
        
        <div class="meta">
            <p><strong>Prepared for:</strong> {client_data['name']}</p>
            {f"<p><strong>Company:</strong> {client_data['company']}</p>" if client_data.get('company') else ''}
            <p><strong>Audit Date:</strong> {datetime.now().strftime('%B %d, %Y')}</p>
            <p style="margin-top: 40px; font-size: 16px;">
                <strong>Prepared by Punkaj Saini</strong><br>
                SEO & Digital Marketing Consultant<br>
                20+ Years Experience<br>
                punkaj@psdigital.io | psdigital.io
            </p>
        </div>
    </div>
    
    <!-- Executive Summary -->
    <div class="section">
        <h1>Executive Summary</h1>
        
        <div class="metric-grid">
            <div class="metric-box">
                <div class="metric-value" style="color: {score_color}">{overall_score}</div>
                <div class="metric-label">SEO Score</div>
            </div>
"""
        
        # Add GSC summary if available
        if gsc_data and gsc_data.get('success'):
            summary = gsc_data['summary']
            html += f"""
            <div class="metric-box">
                <div class="metric-value">{summary['total_clicks']:,}</div>
                <div class="metric-label">Clicks (28 days)</div>
            </div>
            <div class="metric-box">
                <div class="metric-value">{summary['avg_position']}</div>
                <div class="metric-label">Avg Position</div>
            </div>
"""
        
        # Add GA4 summary if available
        if ga4_data and ga4_data.get('success') and ga4_data.get('overall'):
            overall = ga4_data['overall']
            html += f"""
            <div class="metric-box">
                <div class="metric-value">{overall['sessions']:,}</div>
                <div class="metric-label">Sessions (28 days)</div>
            </div>
            <div class="metric-box">
                <div class="metric-value">{overall['users']:,}</div>
                <div class="metric-label">Users</div>
            </div>
"""
        
        html += """
        </div>
        
        <h2>Key Findings</h2>
        <div class="info-box">
"""
        
        # Technical findings
        html += f"""
            <h3>Technical Infrastructure</h3>
            <ul>
                <li class="{'status-good' if technical_findings.get('has_robots_txt') else 'status-critical'}">
                    robots.txt: {'✓ Found' if technical_findings.get('has_robots_txt') else '✗ Missing'}
                </li>
                <li class="{'status-good' if technical_findings.get('has_sitemap') else 'status-critical'}">
                    sitemap.xml: {'✓ Found' if technical_findings.get('has_sitemap') else '✗ Missing'}
                </li>
                <li class="{'status-good' if has_blog else 'status-warning'}">
                    Blog/Content Section: {'✓ Found' if has_blog else '✗ Not Found'}
                </li>
            </ul>
"""
        
        # Page findings
        if pages_data:
            homepage = pages_data[0]
            html += f"""
            <h3>Homepage Optimization</h3>
            <ul>
                <li class="{'status-good' if 50 <= homepage['title_length'] <= 60 else 'status-warning'}">
                    Title Tag: {homepage['title_length']} characters
                </li>
                <li class="{'status-good' if 120 <= homepage['meta_length'] <= 160 else 'status-warning'}">
                    Meta Description: {homepage['meta_length']} characters
                </li>
                <li class="{'status-good' if homepage['h1_count'] == 1 else 'status-critical'}">
                    H1 Tags: {homepage['h1_count']} found
                </li>
                <li class="{'status-good' if homepage['load_time'] < 3 else 'status-warning'}">
                    Page Load Time: {homepage['load_time']}s
                </li>
                <li class="{'status-good' if homepage['schemas'] else 'status-critical'}">
                    Schema Markup: {', '.join(homepage['schemas']) if homepage['schemas'] else 'None detected'}
                </li>
            </ul>
"""
        
        html += """
        </div>
    </div>
"""
        
        # Google Search Console Section
        if gsc_data and gsc_data.get('success'):
            html += """
    <div class="section">
        <h1>Google Search Console Data</h1>
        <p style="color: #64748b; font-size: 14px;">Last 28 days of search performance data</p>
        
        <h2>Top Search Queries</h2>
        <table>
            <thead>
                <tr>
                    <th>Query</th>
                    <th>Clicks</th>
                    <th>Impressions</th>
                    <th>CTR</th>
                    <th>Position</th>
                </tr>
            </thead>
            <tbody>
"""
            
            for query in gsc_data['queries'][:15]:
                html += f"""
                <tr>
                    <td>{query['keys'][0]}</td>
                    <td>{query.get('clicks', 0)}</td>
                    <td>{query.get('impressions', 0):,}</td>
                    <td>{round(query.get('ctr', 0) * 100, 2)}%</td>
                    <td>{round(query.get('position', 0), 1)}</td>
                </tr>
"""
            
            html += """
            </tbody>
        </table>
        
        <h2>Top Performing Pages</h2>
        <table>
            <thead>
                <tr>
                    <th>Page</th>
                    <th>Clicks</th>
                    <th>Impressions</th>
                    <th>CTR</th>
                </tr>
            </thead>
            <tbody>
"""
            
            for page in gsc_data['pages'][:10]:
                html += f"""
                <tr>
                    <td style="font-size: 12px;">{page['keys'][0]}</td>
                    <td>{page.get('clicks', 0)}</td>
                    <td>{page.get('impressions', 0):,}</td>
                    <td>{round(page.get('ctr', 0) * 100, 2)}%</td>
                </tr>
"""
            
            html += """
            </tbody>
        </table>
    </div>
"""
        
        # Google Analytics Section
        if ga4_data and ga4_data.get('success') and ga4_data.get('overall'):
            html += """
    <div class="section">
        <h1>Google Analytics Data</h1>
        <p style="color: #64748b; font-size: 14px;">Last 28 days of website traffic and user behavior</p>
        
        <h2>Traffic Overview</h2>
        <div class="metric-grid">
"""
            
            overall = ga4_data['overall']
            html += f"""
            <div class="metric-box">
                <div class="metric-value">{overall['sessions']:,}</div>
                <div class="metric-label">Sessions</div>
            </div>
            <div class="metric-box">
                <div class="metric-value">{overall['users']:,}</div>
                <div class="metric-label">Users</div>
            </div>
            <div class="metric-box">
                <div class="metric-value">{overall['pageviews']:,}</div>
                <div class="metric-label">Pageviews</div>
            </div>
            <div class="metric-box">
                <div class="metric-value">{overall['bounce_rate']}%</div>
                <div class="metric-label">Bounce Rate</div>
            </div>
            <div class="metric-box">
                <div class="metric-value">{int(overall['avg_session_duration'])}s</div>
                <div class="metric-label">Avg Session Duration</div>
            </div>
"""
            
            html += """
        </div>
        
        <h2>Top Pages by Traffic</h2>
        <table>
            <thead>
                <tr>
                    <th>Page</th>
                    <th>Pageviews</th>
                    <th>Sessions</th>
                </tr>
            </thead>
            <tbody>
"""
            
            for page in ga4_data['top_pages'][:10]:
                html += f"""
                <tr>
                    <td style="font-size: 12px;">{page['page']}</td>
                    <td>{page['pageviews']:,}</td>
                    <td>{page['sessions']:,}</td>
                </tr>
"""
            
            html += """
            </tbody>
        </table>
        
        <h2>Traffic Sources</h2>
        <table>
            <thead>
                <tr>
                    <th>Source</th>
                    <th>Sessions</th>
                </tr>
            </thead>
            <tbody>
"""
            
            for source in ga4_data['traffic_sources'][:10]:
                html += f"""
                <tr>
                    <td>{source['source']}</td>
                    <td>{source['sessions']:,}</td>
                </tr>
"""
            
            html += """
            </tbody>
        </table>
    </div>
"""
        
        # Page-by-Page Analysis
        html += """
    <div class="section">
        <h1>Page-by-Page Analysis</h1>
"""
        
        for page in pages_data:
            html += f"""
        <h2>{page['page_name']}</h2>
        <p style="color: #64748b; font-size: 12px; margin-top: -10px;">{page['url']}</p>
        
        <div class="metric-grid">
            <div class="metric-box">
                <div class="metric-value {'status-good' if 50 <= page['title_length'] <= 60 else 'status-warning'}">{page['title_length']}</div>
                <div class="metric-label">Title Length (chars)</div>
            </div>
            <div class="metric-box">
                <div class="metric-value {'status-good' if 120 <= page['meta_length'] <= 160 else 'status-warning'}">{page['meta_length']}</div>
                <div class="metric-label">Meta Desc (chars)</div>
            </div>
            <div class="metric-box">
                <div class="metric-value {'status-good' if page['load_time'] < 3 else 'status-warning'}">{page['load_time']}s</div>
                <div class="metric-label">Load Time</div>
            </div>
            <div class="metric-box">
                <div class="metric-value">{page['page_size_kb']} KB</div>
                <div class="metric-label">Page Size</div>
            </div>
            <div class="metric-box">
                <div class="metric-value {'status-good' if page['h1_count'] == 1 else 'status-critical'}">{page['h1_count']}</div>
                <div class="metric-label">H1 Tags</div>
            </div>
            <div class="metric-box">
                <div class="metric-value {'status-critical' if page['resources']['images_without_alt'] > 0 else 'status-good'}">{page['resources']['images_without_alt']}</div>
                <div class="metric-label">Images Missing ALT</div>
            </div>
        </div>
        
        <div class="info-box">
            <p><strong>Title:</strong> {page['title']}</p>
            <p><strong>Meta Description:</strong> {page['meta_description']}</p>
            <p><strong>Schema Markup:</strong> {', '.join(page['schemas']) if page['schemas'] else 'None detected'}</p>
        </div>
"""
        
        html += """
    </div>
"""
        
        # Recommendations
        html += f"""
    <div class="section">
        <h1>Recommendations & Action Plan</h1>
        
        <div style="white-space: pre-wrap; line-height: 1.8;">
{recommendations}
        </div>
    </div>
    
    <!-- Final Page -->
    <div class="section">
        <h1>Next Steps</h1>
        
        <div class="info-box">
            <h3>Ready to improve your SEO?</h3>
            <p>This audit has identified key opportunities to improve your website's search engine visibility and organic traffic.</p>
            
            <p><strong>I can help you:</strong></p>
            <ul>
                <li>Implement these recommendations</li>
                <li>Create a 90-day SEO roadmap</li>
                <li>Optimize existing content</li>
                <li>Generate new SEO-optimized content</li>
                <li>Monitor rankings and traffic</li>
                <li>Provide ongoing SEO support</li>
            </ul>
            
            <p style="margin-top: 30px;">
                <strong>Let's schedule a call to discuss your digital growth strategy.</strong>
            </p>
            
            <p style="margin-top: 30px; text-align: center; font-size: 16px;">
                <strong>Punkaj Saini</strong><br>
                SEO & Digital Marketing Consultant<br>
                20+ Years Experience<br><br>
                📧 punkaj@psdigital.io<br>
                🌐 psdigital.io<br>
                💼 linkedin.com/in/punkaj
            </p>
        </div>
    </div>
    
</body>
</html>
"""
        
        return html
    
def _html_to_pdf(self, html_content, website_name):
        """Convert HTML to PDF and return file path"""
        
        # Create temp file
        temp_dir = tempfile.gettempdir()
        safe_name = website_name.replace('https://', '').replace('http://', '').replace('/', '_')
        pdf_filename = f"SEO_Audit_{safe_name}_{datetime.now().strftime('%Y%m%d')}.pdf"
        pdf_path = os.path.join(temp_dir, pdf_filename)
        
        # Generate PDF using xhtml2pdf
        with open(pdf_path, "wb") as pdf_file:
            pisa_status = pisa.CreatePDF(html_content, dest=pdf_file)
        
        if pisa_status.err:
            raise Exception(f"PDF generation failed with error code: {pisa_status.err}")
        
        return pdf_path
