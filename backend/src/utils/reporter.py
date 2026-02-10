from pathlib import Path
from src.utils.database import get_db
import base64

class ActivityReporter:
    def __init__(self, output_file="logs/latest_report.html"):
        self.db = get_db()
        self.output_file = output_file
        
    def generate(self):
        apps = self.db.get_recent_applications(limit=10)
        
        html = """
        <!DOCTYPE html>
        <html>
        <head>
            <title>PaperPlane Activity</title>
            <meta http-equiv="refresh" content="30"> <!-- Auto refresh every 30s -->
            <style>
                body { font-family: sans-serif; max-width: 900px; margin: 0 auto; padding: 20px; background: #f0f2f5; }
                h1 { color: #333; }
                .card { background: white; border-radius: 8px; padding: 15px; margin-bottom: 20px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
                .status { font-weight: bold; text-transform: uppercase; font-size: 0.8em; padding: 4px 8px; border-radius: 4px; }
                .status.applied { background: #d4edda; color: #155724; }
                .status.failed { background: #f8d7da; color: #721c24; }
                .status.needs_review { background: #fff3cd; color: #856404; }
                .timestamp { color: #888; font-size: 0.9em; }
                .screenshots { display: flex; gap: 10px; overflow-x: auto; margin-top: 10px; }
                .screenshots img { height: 150px; border: 1px solid #ddd; border-radius: 4px; }
                .log-line { font-family: monospace; font-size: 0.9em; color: #555; border-left: 3px solid #eee; padding-left: 8px; margin: 2px 0; }
            </style>
        </head>
        <body>
            <h1>Recent Activity</h1>
        """
        
        if not apps:
            html += "<p>No applications found yet.</p>"
        
        for app in apps:
            status_class = app.status.value.lower()
            html += f"""
            <div class="card">
                <div style="display:flex; justify-content:space-between; align-items:center;">
                    <h2>{app.job_title} <span style="font-weight:normal">at {app.company}</span></h2>
                    <span class="status {status_class}">{app.status.value}</span>
                </div>
                <div class="timestamp">{app.created_at}</div>
                
                <div style="margin: 10px 0;">
                    <strong>Application Log:</strong>
                    {"".join([f'<div class="log-line">{log}</div>' for log in app.logs[-5:]])}
                </div>
            """
            
            if app.screenshots:
                html += '<div class="screenshots">'
                for shot_path in app.screenshots:
                    if Path(shot_path).exists():
                        # Convert to base64 to embed directly so it's portable
                        with open(shot_path, "rb") as img_file:
                             b64_str = base64.b64encode(img_file.read()).decode()
                             html += f'<img src="data:image/png;base64,{b64_str}" title="{Path(shot_path).name}">'
                html += '</div>'
                
            html += "</div>"
            
        html += """
        </body>
        </html>
        """
        
        with open(self.output_file, "w") as f:
            f.write(html)
        
        return self.output_file

if __name__ == "__main__":
    reporter = ActivityReporter()
    path = reporter.generate()
    print(f"Report generated at: {path}")
