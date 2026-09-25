import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.application import MIMEApplication
from dotenv import load_dotenv
import json

load_dotenv()


class EmailSender:
    def __init__(self):
        self.host = os.getenv('EMAIL_HOST', 'smtp.example.com')
        self.port = int(os.getenv('EMAIL_PORT', 587))
        self.user = os.getenv('EMAIL_USER', '')
        self.password = os.getenv('EMAIL_PASSWORD', '')
        self.default_recipients = os.getenv('EMAIL_RECIPIENTS', '').split(',') if os.getenv('EMAIL_RECIPIENTS') else []
    
    def send_meeting_summary(self, meeting, recipients=None):
        if not recipients:
            recipients = self.default_recipients
        
        if not recipients or not self.user:
            print("Email configuration incomplete, skipping email send")
            return False
        
        try:
            msg = MIMEMultipart()
            msg['From'] = self.user
            msg['To'] = ', '.join(recipients)
            msg['Subject'] = f"【靛蓝纪要】{meeting.get('summary', {}).get('series_theme', '手工扎染系列')}产品开发会议"
            
            summary = meeting.get('summary', {})
            summary_text = summary.get('summary', '')
            cost_breakdown = summary.get('cost_breakdown', {})
            
            html_content = self._build_html_email(meeting, summary_text, cost_breakdown)
            
            msg.attach(MIMEText(html_content, 'html', 'utf-8'))
            
            csv_attachment = self._build_cost_csv(cost_breakdown)
            if csv_attachment:
                part = MIMEApplication(csv_attachment, Name='成本核算.csv')
                part['Content-Disposition'] = 'attachment; filename="成本核算.csv"'
                msg.attach(part)
            
            transcript_text = self._build_transcript_text(meeting)
            part2 = MIMEApplication(transcript_text.encode('utf-8'), Name='会议转录.txt')
            part2['Content-Disposition'] = 'attachment; filename="会议转录.txt"'
            msg.attach(part2)
            
            with smtplib.SMTP(self.host, self.port) as server:
                server.starttls()
                server.login(self.user, self.password)
                server.send_message(msg)
            
            print(f"Email sent successfully to {recipients}")
            return True
            
        except Exception as e:
            print(f"Email send failed: {e}")
            return False
    
    def _build_html_email(self, meeting, summary_text, cost_breakdown):
        design_data = meeting.get('design_data', {})
        
        html = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <style>
        body {{ font-family: 'Microsoft YaHei', sans-serif; line-height: 1.6; color: #333; }}
        .header {{ background: linear-gradient(135deg, #1e3a5f 0%, #2d5a87 100%); color: white; padding: 30px; text-align: center; }}
        .content {{ padding: 30px; background: #f8f9fa; }}
        .section {{ background: white; padding: 20px; margin-bottom: 20px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }}
        .section-title {{ font-size: 18px; font-weight: bold; color: #1e3a5f; border-bottom: 2px solid #2d5a87; padding-bottom: 10px; margin-bottom: 15px; }}
        .cost-table {{ width: 100%; border-collapse: collapse; margin-top: 15px; }}
        .cost-table th, .cost-table td {{ padding: 12px; text-align: left; border-bottom: 1px solid #e0e0e0; }}
        .cost-table th {{ background: #f5f7fa; color: #1e3a5f; }}
        .total-row {{ font-weight: bold; background: #f0f4f8; }}
        .highlight {{ color: #2d5a87; font-weight: bold; }}
        .footer {{ text-align: center; padding: 20px; color: #666; font-size: 12px; }}
        .pattern-grid {{ display: flex; gap: 10px; flex-wrap: wrap; }}
        .pattern-item {{ background: #e8f0f8; padding: 8px 15px; border-radius: 20px; color: #1e3a5f; }}
    </style>
</head>
<body>
    <div class="header">
        <h1>靛蓝纪要</h1>
        <p>手工扎染工坊产品开发会议纪要</p>
        <p style="font-size: 14px; opacity: 0.8;">{meeting.get('timestamp', '')}</p>
    </div>
    <div class="content">
        <div class="section">
            <div class="section-title">系列主题</div>
            <h2 class="highlight">{meeting.get('summary', {}).get('series_theme', '手工扎染系列')}</h2>
        </div>
        
        <div class="section">
            <div class="section-title">工艺要点</div>
            <div class="pattern-grid">
                <span class="pattern-item">面料：{design_data.get('fabric_type', '棉麻')}</span>
                <span class="pattern-item">复杂度：{design_data.get('complexity', '中等')}</span>
                <span class="pattern-item">数量：{design_data.get('quantity', '1')}件</span>
            </div>
        </div>
        
        <div class="section">
            <div class="section-title">成本核算</div>
            <table class="cost-table">
                <tr>
                    <th>项目</th>
                    <th>成本（元）</th>
                    <th>占比</th>
                </tr>
                <tr><td>面料成本</td><td>{cost_breakdown.get('fabric_cost', 0)}</td><td>{cost_breakdown.get('fabric_percentage', '0%')}</td></tr>
                <tr><td>染料成本</td><td>{cost_breakdown.get('dye_cost', 0)}</td><td>{cost_breakdown.get('dye_percentage', '0%')}</td></tr>
                <tr><td>人工成本</td><td>{cost_breakdown.get('labor_cost', 0)}</td><td>{cost_breakdown.get('labor_percentage', '0%')}</td></tr>
                <tr><td>水电能耗</td><td>{cost_breakdown.get('utility_cost', 0)}</td><td>{cost_breakdown.get('utility_percentage', '0%')}</td></tr>
                <tr><td>其他费用</td><td>{cost_breakdown.get('other_cost', 0)}</td><td>{cost_breakdown.get('other_percentage', '0%')}</td></tr>
                <tr class="total-row"><td>总成本</td><td>{cost_breakdown.get('total_cost', 0)}</td><td>100%</td></tr>
                <tr class="total-row"><td>建议零售价</td><td colspan="2" class="highlight">{cost_breakdown.get('suggested_retail', 0)} 元</td></tr>
            </table>
        </div>
        
        <div class="section">
            <div class="section-title">会议摘要</div>
            <div style="white-space: pre-wrap; line-height: 1.8;">{summary_text[:2000]}...</div>
            <p style="color: #666; font-size: 14px; margin-top: 15px;">完整内容请查看附件</p>
        </div>
    </div>
    <div class="footer">
        <p>靛蓝纪要 - 手工扎染工坊产品开发系统</p>
        <p>此邮件为系统自动发送，请勿直接回复</p>
    </div>
</body>
</html>
"""
        return html
    
    def _build_cost_csv(self, cost_breakdown):
        if not cost_breakdown:
            return None
        
        csv = "项目,成本(元),占比\n"
        csv += f"面料成本,{cost_breakdown.get('fabric_cost', 0)},{cost_breakdown.get('fabric_percentage', '0%')}\n"
        csv += f"染料成本,{cost_breakdown.get('dye_cost', 0)},{cost_breakdown.get('dye_percentage', '0%')}\n"
        csv += f"人工成本,{cost_breakdown.get('labor_cost', 0)},{cost_breakdown.get('labor_percentage', '0%')}\n"
        csv += f"水电能耗,{cost_breakdown.get('utility_cost', 0)},{cost_breakdown.get('utility_percentage', '0%')}\n"
        csv += f"其他费用,{cost_breakdown.get('other_cost', 0)},{cost_breakdown.get('other_percentage', '0%')}\n"
        csv += f"总成本,{cost_breakdown.get('total_cost', 0)},100%\n"
        csv += f"建议零售价,{cost_breakdown.get('suggested_retail', 0)},\n"
        
        return csv.encode('utf-8-sig')
    
    def _build_transcript_text(self, meeting):
        transcript = meeting.get('transcript', {})
        segments = transcript.get('segments', [])
        
        text = f"会议转录 - {meeting.get('timestamp', '')}\n"
        text += "=" * 50 + "\n\n"
        
        for seg in segments:
            role = seg.get('role', '参与者')
            speaker = seg.get('speaker', '未知')
            time_start = seg.get('start', 0)
            text += f"[{time_start:.1f}s] {role} {speaker}:\n"
            text += f"  {seg.get('text', '')}\n\n"
        
        return text
