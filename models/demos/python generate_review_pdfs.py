#!/usr/bin/env python3
"""
Employee Review Form PDF Generator - Windows Compatible
Converts HTML review forms to PDF documents using Playwright

Requirements:
pip install playwright jinja2
playwright install chromium

Usage:
python generate_review_pdfs.py
"""

import os
import sys
import asyncio
from pathlib import Path
from datetime import datetime
from jinja2 import Template

try:
    from playwright.async_api import async_playwright
except ImportError:
    print("❌ Playwright not installed. Please run:")
    print("pip install playwright")
    print("playwright install chromium")
    sys.exit(1)


class ReviewPDFGenerator:
    def __init__(self, output_dir="generated_pdfs"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)

        # Employee data for template substitution
        self.employee_data = {
            'employee_id': 'EMP001',
            'employee_name': 'John Smith',
            'position': 'Maintenance Technician',
            'department': 'Operations',
            'hire_date': '2022-03-15',
            'supervisor': 'Jane Doe',
            'review_date': datetime.now().strftime('%Y-%m-%d'),
            'review_period': '2023-2024',
            'attendance_rate': '97.1%',
            'training_completed': '12/15',
            'training_percentage': '80%',
            'lockout_count': '3',
            'lockout_dates': '2024-03-15, 2024-06-08, 2024-07-30',
            'safety_incidents': '0',
            'overall_completion': '72%',
            'total_competencies': '97',
            'completed_competencies': '70',
            'remaining_competencies': '27'
        }

    def get_base_css(self):
        """Common CSS for all versions"""
        return """
        @page {
            size: letter;
            margin: 0.5in;
        }
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        body {
            font-family: 'Arial', sans-serif;
            font-size: 10px;
            line-height: 1.3;
            color: #333;
            background: white;
        }
        .header {
            text-align: center;
            border-bottom: 2px solid #333;
            padding-bottom: 15px;
            margin-bottom: 20px;
        }
        .section {
            border: 1px solid #ddd;
            padding: 12px;
            margin-bottom: 15px;
            background: #fafafa;
        }
        .form-group {
            margin-bottom: 8px;
        }
        .form-control {
            width: 100%;
            padding: 3px 5px;
            border: 1px solid #ccc;
            font-size: 9px;
            background: white;
        }
        """

    def get_version1_html(self):
        """Version 1: Modern Professional"""
        return """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>Employee Review - Modern Professional</title>
    <style>
        """ + self.get_base_css() + """
        .form-layout {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 20px;
        }
        .progress-grid {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 8px;
            margin-top: 8px;
        }
        .progress-item {
            text-align: center;
            border: 1px solid #ddd;
            padding: 6px;
            background: white;
        }
        .progress-bar {
            width: 100%;
            height: 8px;
            background: #e0e0e0;
            margin: 3px 0;
        }
        .progress-fill {
            height: 100%;
        }
        .level1 { background: #4CAF50; }
        .level2 { background: #2196F3; }
        .level3 { background: #FF9800; }
        .maintenance { background: #9C27B0; }
        .checkbox {
            width: 12px;
            height: 12px;
            border: 1px solid #333;
            margin-right: 8px;
            display: inline-block;
        }
        .checked {
            background: #333;
        }
        .notes-area {
            width: 100%;
            height: 100px;
            border: 1px solid #333;
            padding: 5px;
            font-size: 9px;
        }
    </style>
</head>
<body>
    <div class="header">
        <h1>EMPLOYEE COMPETENCY REVIEW FORM</h1>
        <p>Annual Performance & Skills Assessment</p>
    </div>

    <div class="form-layout">
        <!-- Left Column -->
        <div>
            <div class="section">
                <h3>EMPLOYEE INFORMATION</h3>
                <p><strong>Employee ID:</strong> {{ employee_id }}</p>
                <p><strong>Name:</strong> {{ employee_name }}</p>
                <p><strong>Position:</strong> {{ position }}</p>
                <p><strong>Department:</strong> {{ department }}</p>
                <p><strong>Supervisor:</strong> {{ supervisor }}</p>
                <p><strong>Review Date:</strong> {{ review_date }}</p>
            </div>

            <div class="section">
                <h3>COMPETENCY PROGRESS</h3>
                <div class="progress-grid">
                    <div class="progress-item">
                        <h4>Level 1</h4>
                        <div class="progress-bar">
                            <div class="progress-fill level1" style="width: 85%"></div>
                        </div>
                        <small>17/20 (85%)</small>
                    </div>
                    <div class="progress-item">
                        <h4>Level 2</h4>
                        <div class="progress-bar">
                            <div class="progress-fill level2" style="width: 60%"></div>
                        </div>
                        <small>9/15 (60%)</small>
                    </div>
                    <div class="progress-item">
                        <h4>Level 3</h4>
                        <div class="progress-bar">
                            <div class="progress-fill level3" style="width: 25%"></div>
                        </div>
                        <small>3/12 (25%)</small>
                    </div>
                    <div class="progress-item">
                        <h4>Maintenance Tech</h4>
                        <div class="progress-bar">
                            <div class="progress-fill maintenance" style="width: 10%"></div>
                        </div>
                        <small>1/10 (10%)</small>
                    </div>
                </div>
            </div>

            <div class="section">
                <h3>ATTENDANCE & ILEARNING</h3>
                <p><strong>Attendance Rate:</strong> {{ attendance_rate }}</p>
                <p><strong>Training Completed:</strong> {{ training_completed }} ({{ training_percentage }})</p>
                <p><strong>Number of Lockouts:</strong> {{ lockout_count }}</p>
                <p><strong>Lockout Dates:</strong> {{ lockout_dates }}</p>
                <p><strong>Safety Incidents:</strong> {{ safety_incidents }}</p>
            </div>
        </div>

        <!-- Right Column -->
        <div>
            <div class="section">
                <h3>COMPETENCY BREAKDOWN</h3>
                <p><strong>🔧 MECHANICAL:</strong> L1: 10/12 | L2: 5/8 | L3: 1/6</p>
                <p><strong>⚡ ELECTRICAL:</strong> L1: 9/10 | L2: 4/7 | L3: 0/5</p>
                <p><strong>🛡️ SAFETY:</strong> L1: 8/8 | L2: 4/6</p>
                <p><strong>⚙️ OPERATIONAL:</strong> L1: 12/15 | Tech: 1/10</p>
            </div>

            <div class="section">
                <h3>DEVELOPMENT GOALS</h3>
                <p><span class="checkbox checked"></span> Complete Level 1 mechanical (3 remaining)</p>
                <p><span class="checkbox checked"></span> Focus on Level 2 electrical (3 remaining)</p>
                <p><span class="checkbox"></span> Begin Level 3 certification</p>
                <p><span class="checkbox"></span> Advanced maintenance course</p>
                <p><span class="checkbox"></span> Safety refresher training</p>
            </div>

            <div class="section">
                <h3>PERFORMANCE RATING</h3>
                <p><span class="checkbox"></span> Exceeds Expectations (4)</p>
                <p><span class="checkbox checked"></span> Meets Expectations (3)</p>
                <p><span class="checkbox"></span> Below Expectations (2)</p>
                <p><span class="checkbox"></span> Unsatisfactory (1)</p>
            </div>

            <div class="section">
                <h3>SUPERVISOR COMMENTS</h3>
                <textarea class="notes-area">{{ employee_name }} consistently demonstrates strong technical skills and reliability. His mechanical competencies are progressing well, and he shows excellent safety awareness. Recommend focusing on electrical Level 2 training to broaden skill set.</textarea>
            </div>
        </div>
    </div>

    <!-- Summary -->
    <div style="display: grid; grid-template-columns: repeat(4, 1fr); gap: 10px; margin-top: 20px; text-align: center; border: 2px solid #333; padding: 10px;">
        <div><strong>{{ overall_completion }}</strong><br><small>Overall Completion</small></div>
        <div><strong>{{ total_competencies }}</strong><br><small>Total Competencies</small></div>
        <div><strong>{{ completed_competencies }}</strong><br><small>Completed</small></div>
        <div><strong>{{ remaining_competencies }}</strong><br><small>Remaining</small></div>
    </div>

    <!-- Signatures -->
    <div style="margin-top: 30px; border-top: 1px solid #333; padding-top: 20px;">
        <div style="display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 30px; text-align: center;">
            <div>
                <div style="border-bottom: 1px solid #333; height: 30px; margin-bottom: 5px;"></div>
                <small>Employee Signature / Date</small>
            </div>
            <div>
                <div style="border-bottom: 1px solid #333; height: 30px; margin-bottom: 5px;"></div>
                <small>Supervisor Signature / Date</small>
            </div>
            <div>
                <div style="border-bottom: 1px solid #333; height: 30px; margin-bottom: 5px;"></div>
                <small>HR Representative / Date</small>
            </div>
        </div>
    </div>
</body>
</html>
"""

    def get_version2_html(self):
        """Version 2: Compact Format"""
        return """
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>Employee Review - Compact</title>
    <style>
        @page { size: letter; margin: 0.4in; }
        body { font-family: 'Times New Roman', serif; font-size: 9px; color: #000; }
        .header { text-align: center; border: 2px solid #000; padding: 10px; margin-bottom: 15px; background: #f0f0f0; }
        .section { border: 1px solid #000; margin-bottom: 10px; }
        .section-header { background: #e0e0e0; padding: 5px 8px; font-weight: bold; border-bottom: 1px solid #000; }
        .section-content { padding: 8px; }
        .three-column { display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 10px; }
    </style>
</head>
<body>
    <div class="header">
        <h1>EMPLOYEE PERFORMANCE REVIEW</h1>
        <p>Competency Assessment & Development Planning</p>
    </div>

    <div class="section">
        <div class="section-header">EMPLOYEE INFORMATION</div>
        <div class="section-content">
            <div class="three-column">
                <div>
                    <p><strong>ID:</strong> {{ employee_id }}</p>
                    <p><strong>Name:</strong> {{ employee_name }}</p>
                </div>
                <div>
                    <p><strong>Position:</strong> {{ position }}</p>
                    <p><strong>Department:</strong> {{ department }}</p>
                </div>
                <div>
                    <p><strong>Review Date:</strong> {{ review_date }}</p>
                    <p><strong>Supervisor:</strong> {{ supervisor }}</p>
                </div>
            </div>
        </div>
    </div>

    <div class="section">
        <div class="section-header">PERFORMANCE SUMMARY</div>
        <div class="section-content">
            <p><strong>Overall Progress:</strong> {{ overall_completion }} ({{ completed_competencies }}/{{ total_competencies }} competencies)</p>
            <p><strong>Attendance:</strong> {{ attendance_rate }} | <strong>Training:</strong> {{ training_completed }} ({{ training_percentage }})</p>
            <p><strong>Safety:</strong> {{ lockout_count }} lockouts, {{ safety_incidents }} incidents</p>
            <p><strong>Lockout Dates:</strong> {{ lockout_dates }}</p>
        </div>
    </div>

    <div class="section">
        <div class="section-header">COMPETENCY LEVELS</div>
        <div class="section-content">
            <p><strong>Level 1:</strong> 85% complete (17/20) | <strong>Level 2:</strong> 60% complete (9/15)</p>
            <p><strong>Level 3:</strong> 25% complete (3/12) | <strong>Maintenance Tech:</strong> 10% complete (1/10)</p>
        </div>
    </div>

    <div class="section">
        <div class="section-header">DEVELOPMENT PRIORITIES</div>
        <div class="section-content">
            <p>☑ Level 1 Mechanical (3 left) | ☑ Level 2 Electrical (3 left)</p>
            <p>☐ Level 3 Certification | ☐ Advanced Maintenance | ☐ Safety Refresher</p>
        </div>
    </div>

    <div style="margin-top: 20px; text-align: center;">
        <p><strong>OVERALL RATING:</strong> ☐ Exceeds (4) | ☑ Meets (3) | ☐ Below (2) | ☐ Unsatisfactory (1)</p>
    </div>

    <div style="margin-top: 20px; border-top: 1px solid #000; padding-top: 10px;">
        <div style="display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 20px; text-align: center;">
            <div>________________<br><small>Employee / Date</small></div>
            <div>________________<br><small>Supervisor / Date</small></div>
            <div>________________<br><small>HR / Date</small></div>
        </div>
    </div>
</body>
</html>
"""

    def get_version3_html(self):
        """Version 3: Dashboard Style"""
        return """
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>Employee Review - Dashboard</title>
    <style>
        @page { size: letter; margin: 0.5in; }
        body { font-family: 'Calibri', sans-serif; font-size: 10px; }
        .header { background: #2c3e50; color: white; text-align: center; padding: 15px; margin-bottom: 20px; border-radius: 8px; }
        .metric-grid { display: grid; grid-template-columns: repeat(4, 1fr); gap: 8px; margin-bottom: 15px; }
        .metric-card { border: 2px solid #ecf0f1; border-radius: 6px; padding: 12px; text-align: center; background: white; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
        .metric-number { font-size: 24px; font-weight: bold; margin-bottom: 3px; }
        .card { background: white; border: 1px solid #bdc3c7; border-radius: 6px; margin-bottom: 12px; overflow: hidden; }
        .card-header { background: #ecf0f1; padding: 8px 12px; font-weight: bold; font-size: 11px; color: #2c3e50; }
        .card-content { padding: 12px; }
        .progress-visual { height: 12px; background: #ecf0f1; border-radius: 6px; overflow: hidden; margin: 5px 0; }
        .progress-bar { height: 100%; }
        .level1 { background: linear-gradient(90deg, #27ae60, #2ecc71); }
        .level2 { background: linear-gradient(90deg, #3498db, #5dade2); }
        .level3 { background: linear-gradient(90deg, #f39c12, #f8c471); }
        .maintenance { background: linear-gradient(90deg, #9b59b6, #bb8fce); }
    </style>
</head>
<body>
    <div class="header">
        <h1>EMPLOYEE PERFORMANCE DASHBOARD</h1>
        <p>{{ employee_name }} - {{ review_date }}</p>
    </div>

    <div class="metric-grid">
        <div class="metric-card">
            <div class="metric-number" style="color: #27ae60;">{{ overall_completion }}</div>
            <div style="font-size: 8px; color: #7f8c8d; font-weight: bold;">OVERALL PROGRESS</div>
        </div>
        <div class="metric-card">
            <div class="metric-number" style="color: #27ae60;">{{ attendance_rate }}</div>
            <div style="font-size: 8px; color: #7f8c8d; font-weight: bold;">ATTENDANCE RATE</div>
        </div>
        <div class="metric-card">
            <div class="metric-number" style="color: #f39c12;">{{ training_percentage }}</div>
            <div style="font-size: 8px; color: #7f8c8d; font-weight: bold;">TRAINING COMPLETE</div>
        </div>
        <div class="metric-card">
            <div class="metric-number" style="color: #e74c3c;">{{ lockout_count }}</div>
            <div style="font-size: 8px; color: #7f8c8d; font-weight: bold;">SAFETY LOCKOUTS</div>
        </div>
    </div>

    <div style="display: grid; grid-template-columns: 1.2fr 0.8fr; gap: 15px;">
        <div>
            <div class="card">
                <div class="card-header">📊 COMPETENCY PROGRESS BY LEVEL</div>
                <div class="card-content">
                    <div style="margin-bottom: 10px;">
                        <div style="display: flex; justify-content: space-between; margin-bottom: 5px;">
                            <span>Level 1 - Basic Skills</span>
                            <span>17/20 (85%)</span>
                        </div>
                        <div class="progress-visual">
                            <div class="progress-bar level1" style="width: 85%"></div>
                        </div>
                    </div>
                    <div style="margin-bottom: 10px;">
                        <div style="display: flex; justify-content: space-between; margin-bottom: 5px;">
                            <span>Level 2 - Intermediate Skills</span>
                            <span>9/15 (60%)</span>
                        </div>
                        <div class="progress-visual">
                            <div class="progress-bar level2" style="width: 60%"></div>
                        </div>
                    </div>
                    <div style="margin-bottom: 10px;">
                        <div style="display: flex; justify-content: space-between; margin-bottom: 5px;">
                            <span>Level 3 - Advanced Skills</span>
                            <span>3/12 (25%)</span>
                        </div>
                        <div class="progress-visual">
                            <div class="progress-bar level3" style="width: 25%"></div>
                        </div>
                    </div>
                    <div>
                        <div style="display: flex; justify-content: space-between; margin-bottom: 5px;">
                            <span>Maintenance Tech - Expert Level</span>
                            <span>1/10 (10%)</span>
                        </div>
                        <div class="progress-visual">
                            <div class="progress-bar maintenance" style="width: 10%"></div>
                        </div>
                    </div>
                </div>
            </div>

            <div class="card">
                <div class="card-header">📚 ILEARNING & SAFETY RECORD</div>
                <div class="card-content">
                    <p><strong>Training Completed:</strong> {{ training_completed }} ({{ training_percentage }})</p>
                    <p><strong>Number of Lockouts:</strong> {{ lockout_count }}</p>
                    <p><strong>Lockout Dates:</strong> {{ lockout_dates }}</p>
                    <p><strong>Safety Incidents:</strong> {{ safety_incidents }}</p>
                </div>
            </div>
        </div>

        <div>
            <div class="card">
                <div class="card-header">⭐ PERFORMANCE RATING</div>
                <div class="card-content">
                    <div style="display: flex; justify-content: center; gap: 15px; padding: 15px;">
                        <div style="text-align: center;">
                            <div style="width: 40px; height: 40px; border: 3px solid #bdc3c7; border-radius: 50%; display: flex; align-items: center; justify-content: center; font-weight: bold; font-size: 14px; margin-bottom: 5px;">4</div>
                            <div style="font-size: 8px; font-weight: bold;">EXCEEDS</div>
                        </div>
                        <div style="text-align: center;">
                            <div style="width: 40px; height: 40px; border: 3px solid #2c3e50; background: #2c3e50; color: white; border-radius: 50%; display: flex; align-items: center; justify-content: center; font-weight: bold; font-size: 14px; margin-bottom: 5px;">3</div>
                            <div style="font-size: 8px; font-weight: bold;">MEETS</div>
                        </div>
                        <div style="text-align: center;">
                            <div style="width: 40px; height: 40px; border: 3px solid #bdc3c7; border-radius: 50%; display: flex; align-items: center; justify-content: center; font-weight: bold; font-size: 14px; margin-bottom: 5px;">2</div>
                            <div style="font-size: 8px; font-weight: bold;">BELOW</div>
                        </div>
                        <div style="text-align: center;">
                            <div style="width: 40px; height: 40px; border: 3px solid #bdc3c7; border-radius: 50%; display: flex; align-items: center; justify-content: center; font-weight: bold; font-size: 14px; margin-bottom: 5px;">1</div>
                            <div style="font-size: 8px; font-weight: bold;">UNSATIS.</div>
                        </div>
                    </div>
                </div>
            </div>

            <div class="card">
                <div class="card-header">🎯 DEVELOPMENT GOALS</div>
                <div class="card-content">
                    <div style="display: grid; grid-template-columns: 1fr; gap: 8px;">
                        <div style="display: flex; align-items: center; padding: 6px; background: #f8f9fa; border-radius: 4px; border-left: 3px solid #27ae60;">
                            <div style="width: 12px; height: 12px; background: #27ae60; margin-right: 8px; border-radius: 2px;"></div>
                            <div style="font-size: 8px;">Complete Level 1 mechanical (3 remaining)</div>
                        </div>
                        <div style="display: flex; align-items: center; padding: 6px; background: #f8f9fa; border-radius: 4px; border-left: 3px solid #27ae60;">
                            <div style="width: 12px; height: 12px; background: #27ae60; margin-right: 8px; border-radius: 2px;"></div>
                            <div style="font-size: 8px;">Focus on Level 2 electrical (3 remaining)</div>
                        </div>
                        <div style="display: flex; align-items: center; padding: 6px; background: #f8f9fa; border-radius: 4px; border-left: 3px solid #3498db;">
                            <div style="width: 12px; height: 12px; border: 2px solid #34495e; margin-right: 8px; border-radius: 2px;"></div>
                            <div style="font-size: 8px;">Begin Level 3 certification program</div>
                        </div>
                        <div style="display: flex; align-items: center; padding: 6px; background: #f8f9fa; border-radius: 4px; border-left: 3px solid #3498db;">
                            <div style="width: 12px; height: 12px; border: 2px solid #34495e; margin-right: 8px; border-radius: 2px;"></div>
                            <div style="font-size: 8px;">Advanced maintenance course</div>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    </div>

    <div style="background: #34495e; color: white; padding: 10px; margin: 15px 0; border-radius: 6px; display: flex; justify-content: space-around; text-align: center;">
        <div><div style="font-size: 16px; font-weight: bold;">{{ total_competencies }}</div><div style="font-size: 8px;">TOTAL COMPETENCIES</div></div>
        <div><div style="font-size: 16px; font-weight: bold;">{{ completed_competencies }}</div><div style="font-size: 8px;">COMPLETED</div></div>
        <div><div style="font-size: 16px; font-weight: bold;">{{ remaining_competencies }}</div><div style="font-size: 8px;">REMAINING</div></div>
        <div><div style="font-size: 16px; font-weight: bold;">{{ overall_completion }}</div><div style="font-size: 8px;">COMPLETION RATE</div></div>
    </div>

    <div style="margin-top: 15px; border-top: 2px solid #34495e; padding-top: 15px;">
        <div style="display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 20px; text-align: center;">
            <div><div style="border-bottom: 2px solid #2c3e50; height: 30px; margin-bottom: 5px;"></div><div style="font-size: 9px; font-weight: bold;">Employee Signature / Date</div></div>
            <div><div style="border-bottom: 2px solid #2c3e50; height: 30px; margin-bottom: 5px;"></div><div style="font-size: 9px; font-weight: bold;">Supervisor Signature / Date</div></div>
            <div><div style="border-bottom: 2px solid #2c3e50; height: 30px; margin-bottom: 5px;"></div><div style="font-size: 9px; font-weight: bold;">HR Representative / Date</div></div>
        </div>
    </div>
</body>
</html>
"""

    def get_version4_html(self):
        """Version 4: Traditional Formal"""
        return """
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>Employee Review - Traditional Formal</title>
    <style>
        @page { size: letter; margin: 0.75in; }
        body { font-family: 'Times New Roman', serif; font-size: 11px; line-height: 1.5; color: #000; }
        .header-section { text-align: center; margin-bottom: 25px; padding-bottom: 15px; border-bottom: 3px double #000; }
        .company-header { font-size: 16px; font-weight: bold; text-transform: uppercase; letter-spacing: 2px; margin-bottom: 5px; }
        .form-title { font-size: 14px; font-weight: bold; margin-bottom: 3px; }
        .section-title { font-size: 12px; font-weight: bold; text-transform: uppercase; text-align: center; background: #f0f0f0; padding: 8px; border: 2px solid #000; margin: 15px 0 10px 0; letter-spacing: 1px; }
        .form-section { margin-bottom: 20px; border: 1px solid #000; padding: 15px; }
        .field-row { display: flex; margin-bottom: 12px; align-items: baseline; }
        .field-label { font-weight: bold; margin-right: 10px; min-width: 120px; text-transform: uppercase; font-size: 10px; }
        .field-line { flex: 1; border-bottom: 1px solid #000; min-height: 20px; padding: 2px 5px; font-size: 11px; }
        .two-column { display: grid; grid-template-columns: 1fr 1fr; gap: 20px; }
        .competency-table { width: 100%; border-collapse: collapse; margin: 10px 0; }
        .competency-table th, .competency-table td { border: 1px solid #000; padding: 6px 8px; text-align: center; font-size: 10px; }
        .competency-table th { background: #f0f0f0; font-weight: bold; text-transform: uppercase; }
        .competency-table td.category { text-align: left; font-weight: bold; background: #f8f8f8; }
        .rating-section { border: 2px solid #000; padding: 15px; margin: 15px 0; }
        .rating-options { display: flex; justify-content: space-around; margin: 15px 0; }
        .rating-option { text-align: center; flex: 1; }
        .rating-box { width: 30px; height: 30px; border: 2px solid #000; margin: 0 auto 5px; display: flex; align-items: center; justify-content: center; font-weight: bold; font-size: 14px; }
        .rating-box.selected { background: #000; color: white; }
        .rating-label { font-size: 9px; font-weight: bold; text-transform: uppercase; }
        .checkbox-item { display: flex; align-items: flex-start; margin-bottom: 8px; }
        .checkbox { width: 15px; height: 15px; border: 2px solid #000; margin-right: 10px; margin-top: 2px; }
        .checkbox.checked { background: #000; }
        .comments-box { width: 100%; height: 120px; border: 2px solid #000; padding: 10px; font-family: 'Times New Roman', serif; font-size: 10px; resize: none; }
        .signature-section { margin-top: 30px; border-top: 3px double #000; padding-top: 20px; }
        .signature-row { display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 30px; margin-top: 20px; }
        .signature-block { text-align: center; }
        .signature-line { border-bottom: 2px solid #000; height: 35px; margin-bottom: 8px; }
        .signature-title { font-size: 9px; font-weight: bold; text-transform: uppercase; }
    </style>
</head>
<body>
    <div class="header-section">
        <div class="company-header">INDUSTRIAL OPERATIONS DIVISION</div>
        <div class="form-title">ANNUAL EMPLOYEE PERFORMANCE EVALUATION</div>
        <div style="font-size: 10px; font-style: italic;">Competency Assessment and Professional Development Review</div>
    </div>

    <div class="section-title">Part I - Employee Information</div>
    <div class="form-section">
        <div class="two-column">
            <div>
                <div class="field-row">
                    <span class="field-label">Employee ID:</span>
                    <span class="field-line">{{ employee_id }}</span>
                </div>
                <div class="field-row">
                    <span class="field-label">Employee Name:</span>
                    <span class="field-line">{{ employee_name }}</span>
                </div>
                <div class="field-row">
                    <span class="field-label">Position Title:</span>
                    <span class="field-line">{{ position }}</span>
                </div>
                <div class="field-row">
                    <span class="field-label">Department:</span>
                    <span class="field-line">{{ department }}</span>
                </div>
            </div>
            <div>
                <div class="field-row">
                    <span class="field-label">Review Date:</span>
                    <span class="field-line">{{ review_date }}</span>
                </div>
                <div class="field-row">
                    <span class="field-label">Review Period:</span>
                    <span class="field-line">{{ review_period }}</span>
                </div>
                <div class="field-row">
                    <span class="field-label">Hire Date:</span>
                    <span class="field-line">03/15/2022</span>
                </div>
                <div class="field-row">
                    <span class="field-label">Supervisor:</span>
                    <span class="field-line">{{ supervisor }}</span>
                </div>
            </div>
        </div>
    </div>

    <div class="section-title">Part II - Attendance and Training Record</div>
    <div class="form-section">
        <div style="display: grid; grid-template-columns: repeat(4, 1fr); gap: 10px; margin: 10px 0; text-align: center;">
            <div style="border: 1px solid #000; padding: 8px;">
                <div style="font-size: 16px; font-weight: bold;">245</div>
                <div style="font-size: 8px; text-transform: uppercase;">Days Scheduled</div>
            </div>
            <div style="border: 1px solid #000; padding: 8px;">
                <div style="font-size: 16px; font-weight: bold;">238</div>
                <div style="font-size: 8px; text-transform: uppercase;">Days Present</div>
            </div>
            <div style="border: 1px solid #000; padding: 8px;">
                <div style="font-size: 16px; font-weight: bold;">{{ attendance_rate }}</div>
                <div style="font-size: 8px; text-transform: uppercase;">Attendance Rate</div>
            </div>
            <div style="border: 1px solid #000; padding: 8px;">
                <div style="font-size: 16px; font-weight: bold;">{{ lockout_count }}</div>
                <div style="font-size: 8px; text-transform: uppercase;">Safety Lockouts</div>
            </div>
        </div>

        <div class="two-column" style="margin-top: 15px;">
            <div>
                <div class="field-row">
                    <span class="field-label">Training Completed:</span>
                    <span class="field-line">{{ training_completed }} ({{ training_percentage }})</span>
                </div>
                <div class="field-row">
                    <span class="field-label">Last Training Date:</span>
                    <span class="field-line">07/22/2024</span>
                </div>
            </div>
            <div>
                <div class="field-row">
                    <span class="field-label">Lockout Dates:</span>
                    <span class="field-line">{{ lockout_dates }}</span>
                </div>
                <div class="field-row">
                    <span class="field-label">Safety Incidents:</span>
                    <span class="field-line">{{ safety_incidents }}</span>
                </div>
            </div>
        </div>

        <div style="margin-top: 15px;">
            <div class="field-row">
                <span class="field-label">Outstanding Training:</span>
                <span class="field-line">Safety Refresher, Equipment Certification, Emergency Response</span>
            </div>
        </div>
    </div>

    <div class="section-title">Part III - Technical Competency Assessment</div>
    <div class="form-section">
        <table class="competency-table">
            <thead>
                <tr>
                    <th>Competency Category</th>
                    <th>Level 1</th>
                    <th>Level 2</th>
                    <th>Level 3</th>
                    <th>Total Progress</th>
                    <th>Completion %</th>
                </tr>
            </thead>
            <tbody>
                <tr>
                    <td class="category">🔧 MECHANICAL SYSTEMS</td>
                    <td>10/12</td>
                    <td>5/8</td>
                    <td>1/6</td>
                    <td>16/26</td>
                    <td><strong>62%</strong></td>
                </tr>
                <tr>
                    <td class="category">⚡ ELECTRICAL SYSTEMS</td>
                    <td>9/10</td>
                    <td>4/7</td>
                    <td>0/5</td>
                    <td>13/22</td>
                    <td><strong>59%</strong></td>
                </tr>
                <tr>
                    <td class="category">🛡️ SAFETY PROTOCOLS</td>
                    <td>8/8</td>
                    <td>4/6</td>
                    <td>—</td>
                    <td>12/14</td>
                    <td><strong>86%</strong></td>
                </tr>
                <tr>
                    <td class="category">⚙️ OPERATIONAL PROCEDURES</td>
                    <td>12/15</td>
                    <td>—</td>
                    <td>—</td>
                    <td>12/15</td>
                    <td><strong>80%</strong></td>
                </tr>
                <tr>
                    <td class="category">🔬 MAINTENANCE TECHNICIAN</td>
                    <td>—</td>
                    <td>—</td>
                    <td>1/10</td>
                    <td>1/10</td>
                    <td><strong>10%</strong></td>
                </tr>
                <tr style="background: #f0f0f0; font-weight: bold;">
                    <td class="category">OVERALL TOTALS</td>
                    <td>39/45</td>
                    <td>13/21</td>
                    <td>2/21</td>
                    <td><strong>54/87</strong></td>
                    <td><strong>62%</strong></td>
                </tr>
            </tbody>
        </table>
    </div>

    <div class="section-title">Part IV - Overall Performance Rating</div>
    <div class="rating-section">
        <div style="text-align: center; margin-bottom: 15px; font-weight: bold; font-size: 12px;">
            SELECT ONE OVERALL PERFORMANCE LEVEL:
        </div>
        <div class="rating-options">
            <div class="rating-option">
                <div class="rating-box">4</div>
                <div class="rating-label">Exceeds<br>Expectations</div>
            </div>
            <div class="rating-option">
                <div class="rating-box selected">3</div>
                <div class="rating-label">Meets<br>Expectations</div>
            </div>
            <div class="rating-option">
                <div class="rating-box">2</div>
                <div class="rating-label">Below<br>Expectations</div>
            </div>
            <div class="rating-option">
                <div class="rating-box">1</div>
                <div class="rating-label">Unsatisfactory<br>Performance</div>
            </div>
        </div>
    </div>

    <div class="section-title">Part V - Professional Development Goals</div>
    <div class="form-section">
        <div style="font-weight: bold; margin-bottom: 10px; text-decoration: underline;">
            Development Priorities for Next Review Period:
        </div>
        <div>
            <div class="checkbox-item">
                <div class="checkbox checked"></div>
                <div style="font-size: 10px; line-height: 1.3;">Complete remaining Level 1 mechanical competencies (3 tasks remaining)</div>
            </div>
            <div class="checkbox-item">
                <div class="checkbox checked"></div>
                <div style="font-size: 10px; line-height: 1.3;">Focus on Level 2 electrical training and assessment (3 tasks remaining)</div>
            </div>
            <div class="checkbox-item">
                <div class="checkbox"></div>
                <div style="font-size: 10px; line-height: 1.3;">Begin Level 3 mechanical certification program</div>
            </div>
            <div class="checkbox-item">
                <div class="checkbox"></div>
                <div style="font-size: 10px; line-height: 1.3;">Enroll in advanced maintenance technician course</div>
            </div>
            <div class="checkbox-item">
                <div class="checkbox"></div>
                <div style="font-size: 10px; line-height: 1.3;">Complete safety Level 2 refresher training</div>
            </div>
            <div class="checkbox-item">
                <div class="checkbox"></div>
                <div style="font-size: 10px; line-height: 1.3;">Participate in leadership development program</div>
            </div>
        </div>
    </div>

    <div class="section-title">Part VI - Supervisor Evaluation and Comments</div>
    <div class="form-section">
        <div style="font-weight: bold; margin-bottom: 8px;">
            Supervisor Assessment (Please provide detailed comments on performance, strengths, and areas for improvement):
        </div>
        <textarea class="comments-box">{{ employee_name }} consistently demonstrates strong technical skills and reliability throughout the review period. His mechanical competencies are progressing well above expectations, and he maintains an excellent safety record with zero incidents.

STRENGTHS:
• Strong foundational mechanical and operational skills
• Excellent attendance record ({{ attendance_rate }}) and punctuality
• Safety-conscious approach to all work activities
• Demonstrates initiative and willingness to learn new procedures
• Reliable team member who can work independently

AREAS FOR DEVELOPMENT:
• Continue focus on electrical systems training to broaden technical skill set
• Complete outstanding safety training requirements promptly
• Consider advanced maintenance technician certification track
• Leadership potential - recommend mentoring opportunities

RECOMMENDATION: {{ employee_name }} shows great potential for advancement and should continue on accelerated development track with focus on electrical competencies and advanced technical training.</textarea>
    </div>

    <div class="signature-section">
        <div style="text-align: center; font-weight: bold; font-size: 12px; margin-bottom: 15px; text-transform: uppercase;">
            Review Acknowledgment and Signatures
        </div>

        <div class="signature-row">
            <div class="signature-block">
                <div class="signature-line"></div>
                <div class="signature-title">Employee Signature</div>
                <div style="margin-top: 10px;">
                    <span style="font-size: 9px;">Date: </span>
                    <span style="border-bottom: 1px solid #000; padding: 0 20px;">____________</span>
                </div>
            </div>
            <div class="signature-block">
                <div class="signature-line"></div>
                <div class="signature-title">Supervisor Signature</div>
                <div style="margin-top: 10px;">
                    <span style="font-size: 9px;">Date: </span>
                    <span style="border-bottom: 1px solid #000; padding: 0 20px;">____________</span>
                </div>
            </div>
            <div class="signature-block">
                <div class="signature-line"></div>
                <div class="signature-title">HR Representative</div>
                <div style="margin-top: 10px;">
                    <span style="font-size: 9px;">Date: </span>
                    <span style="border-bottom: 1px solid #000; padding: 0 20px;">____________</span>
                </div>
            </div>
        </div>
    </div>

    <div style="text-align: center; margin-top: 20px; font-size: 9px;">
        <div style="margin-bottom: 5px;">
            Employee acknowledges receipt of this performance evaluation and understands it will be placed in their permanent personnel file.
        </div>
        <div>
            <strong>Next Scheduled Review Date:</strong> _________________________ | 
            <strong>HR File Reference:</strong> _________________________ |
            <strong>Form Version:</strong> 2024.3
        </div>
    </div>
</body>
</html>
"""

    def customize_template(self, html_template, employee_data=None):
        """Replace template variables with actual data"""
        if employee_data is None:
            employee_data = self.employee_data

        template = Template(html_template)
        return template.render(**employee_data)

    async def generate_pdf(self, html_content, output_filename):
        """Generate PDF from HTML content using Playwright"""
        try:
            async with async_playwright() as p:
                browser = await p.chromium.launch()
                page = await browser.new_page()

                # Set content and wait for it to load
                await page.set_content(html_content, wait_until='networkidle')

                # Generate PDF with print settings
                output_path = self.output_dir / output_filename
                await page.pdf(
                    path=str(output_path),
                    format='Letter',
                    margin={
                        'top': '0.5in',
                        'right': '0.5in',
                        'bottom': '0.5in',
                        'left': '0.5in'
                    },
                    print_background=True,
                    prefer_css_page_size=True
                )

                await browser.close()

                print(f"✅ Successfully generated: {output_path}")
                return output_path

        except Exception as e:
            print(f"❌ Error generating {output_filename}: {str(e)}")
            return None

    async def generate_all_pdfs(self, employee_data=None):
        """Generate all 4 PDF versions"""
        if employee_data:
            self.employee_data.update(employee_data)

        templates = {
            'version1': {
                'name': 'Modern Professional',
                'html': self.get_version1_html(),
                'filename': 'employee_review_v1_modern.pdf'
            },
            'version2': {
                'name': 'Compact Efficient',
                'html': self.get_version2_html(),
                'filename': 'employee_review_v2_compact.pdf'
            },
            'version3': {
                'name': 'Visual Dashboard',
                'html': self.get_version3_html(),
                'filename': 'employee_review_v3_dashboard.pdf'
            },
            'version4': {
                'name': 'Traditional Formal',
                'html': self.get_version4_html(),
                'filename': 'employee_review_v4_formal.pdf'
            }
        }

        generated_files = []

        print(f"🚀 Generating PDFs for employee: {self.employee_data['employee_name']}")
        print(f"📁 Output directory: {self.output_dir.absolute()}")
        print("=" * 60)

        for version_key, template_info in templates.items():
            print(f"📄 Generating {template_info['name']}...")

            # Customize template with data
            html_content = self.customize_template(
                template_info['html'],
                self.employee_data
            )

            # Generate PDF
            pdf_path = await self.generate_pdf(
                html_content,
                template_info['filename']
            )

            if pdf_path:
                generated_files.append(pdf_path)

        print("=" * 60)
        print(f"✅ Generated {len(generated_files)} PDF files successfully!")
        return generated_files

    async def generate_custom_pdf(self, version_name, custom_data, output_filename=None):
        """Generate a single PDF with custom employee data"""
        templates = {
            'version1': self.get_version1_html(),
            'version2': self.get_version2_html(),
            'version3': self.get_version3_html(),
            'version4': self.get_version4_html()
        }

        if version_name not in templates:
            print(f"❌ Unknown version: {version_name}")
            print(f"Available versions: {list(templates.keys())}")
            return None

        # Merge custom data with defaults
        employee_data = {**self.employee_data, **custom_data}

        # Generate filename if not provided
        if not output_filename:
            emp_id = employee_data.get('employee_id', 'unknown')
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            output_filename = f"review_{emp_id}_{version_name}_{timestamp}.pdf"

        html_content = self.customize_template(templates[version_name], employee_data)

        return await self.generate_pdf(html_content, output_filename)


async def main():
    """Main function to demonstrate usage"""

    # Check if playwright is installed
    try:
        from playwright.async_api import async_playwright
    except ImportError:
        print("❌ Playwright not installed. Please run:")
        print("pip install playwright")
        print("playwright install chromium")
        sys.exit(1)

    # Initialize generator
    generator = ReviewPDFGenerator()

    # Example 1: Generate all PDFs with default data
    print("🔥 Example 1: Generating all 4 versions with default data")
    generated_files = await generator.generate_all_pdfs()

    # Example 2: Generate PDFs with custom employee data
    print("\n🔥 Example 2: Generating with custom employee data")
    custom_employee_data = {
        'employee_id': 'EMP002',
        'employee_name': 'Sarah Johnson',
        'position': 'Senior Technician',
        'department': 'Maintenance',
        'supervisor': 'Mike Wilson',
        'attendance_rate': '99.2%',
        'training_completed': '15/15',
        'training_percentage': '100%',
        'lockout_count': '1',
        'overall_completion': '89%'
    }

    custom_files = await generator.generate_all_pdfs(custom_employee_data)

    # Example 3: Generate single PDF with specific version
    print("\n🔥 Example 3: Generating single version")
    single_pdf = await generator.generate_custom_pdf(
        'version1',
        {'employee_name': 'Test Employee', 'employee_id': 'TEST001'},
        'test_review.pdf'
    )

    print("\n🎉 All done! Check the 'generated_pdfs' folder for your files.")


if __name__ == "__main__":
    asyncio.run(main())