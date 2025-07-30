"""
use http://localhost:5000/task_evaul.html
Simple integration between evaluation form and database
"""

import json
import sys
import os
from datetime import datetime

# Add current directory to Python path to ensure imports work
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

# Try to import the database module with error handling
try:
    from db_evaul_task import SimpleTaskEvaluationDB
    print("✓ Successfully imported database module")
except ImportError as e:
    print(f"❌ Error importing database module: {e}")
    print(f"Current directory: {os.getcwd()}")
    print(f"Python path: {sys.path}")
    print("Available files in current directory:")
    for file in os.listdir('..'):
        if file.endswith('.py'):
            print(f"  - {file}")
    raise


class TaskEvaluationManager:
    """Simple manager for task evaluations"""

    def __init__(self, db_path="task_evaluations.db"):
        self.db = SimpleTaskEvaluationDB(f"sqlite:///{db_path}")
        self.db.create_tables()
        self.db.setup_reference_data()

    def save_form_data(self, form_json):
        """Save data from evaluation form"""
        try:
            # Parse form data
            form_data = json.loads(form_json) if isinstance(form_json, str) else form_json

            # Map form fields to database structure
            evaluation_data = {
                'task_name': form_data.get('taskName', ''),
                'task_description': form_data.get('taskDescription', ''),
                'equipment_system': form_data.get('equipment', ''),  # Fixed field name
                'location': form_data.get('location', ''),
                'disciplines': form_data.get('disciplines', []),
                'modifiers': form_data.get('modifiers', []),
                'technical_score': int(form_data.get('technical', 0)) if form_data.get('technical') else None,
                'problem_score': int(form_data.get('problem', 0)) if form_data.get('problem') else None,
                'decision_score': int(form_data.get('decision', 0)) if form_data.get('decision') else None,
                'impact_score': int(form_data.get('impact', 0)) if form_data.get('impact') else None,
                'supervision_score': int(form_data.get('supervision', 0)) if form_data.get('supervision') else None,
                'tools_score': int(form_data.get('tools', 0)) if form_data.get('tools') else None,
                'prerequisites': form_data.get('prerequisites', ''),
                'safety_considerations': form_data.get('safetyConsiderations', ''),
                'required_tools': form_data.get('tools_required', ''),
                'estimated_time': form_data.get('estimatedTime', ''),
                'task_frequency': form_data.get('frequency', ''),
                'success_criteria': form_data.get('successCriteria', ''),
                'quality_standards': form_data.get('qualityStandards', ''),
                'evaluator_name': form_data.get('evaluatorName', 'Unknown'),
                'evaluation_notes': form_data.get('evaluationNotes', '')
            }

            # Save to database
            evaluation_id = self.db.save_evaluation(evaluation_data)

            return {
                'success': True,
                'evaluation_id': evaluation_id,
                'message': f'Evaluation saved successfully with ID: {evaluation_id}'
            }

        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'message': f'Error saving evaluation: {str(e)}'
            }

    def get_evaluation_summary(self, evaluation_id):
        """Get evaluation summary by ID"""
        try:
            evaluation = self.db.get_evaluation(evaluation_id)
            if evaluation:
                return {
                    'success': True,
                    'data': evaluation
                }
            else:
                return {
                    'success': False,
                    'message': 'Evaluation not found'
                }
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'message': f'Error retrieving evaluation: {str(e)}'
            }

    def search_evaluations(self, **kwargs):
        """Search evaluations with filters"""
        try:
            results = self.db.search_evaluations(**kwargs)
            return {
                'success': True,
                'data': results,
                'count': len(results)
            }
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'message': f'Error searching evaluations: {str(e)}'
            }

    def get_all_evaluations(self):
        """Get all evaluations"""
        try:
            results = self.db.get_all_evaluations()
            return {
                'success': True,
                'data': results,
                'count': len(results)
            }
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'message': f'Error retrieving evaluations: {str(e)}'
            }

    def get_statistics(self):
        """Get evaluation statistics"""
        try:
            stats = self.db.get_summary_statistics()
            return {
                'success': True,
                'data': stats
            }
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'message': f'Error getting statistics: {str(e)}'
            }

    def export_evaluations(self, format='json'):
        """Export all evaluations"""
        try:
            evaluations = self.db.get_all_evaluations()

            if format.lower() == 'json':
                return {
                    'success': True,
                    'data': evaluations,
                    'format': 'json'
                }
            elif format.lower() == 'csv':
                import csv
                import io

                # Create CSV string
                output = io.StringIO()
                if evaluations:
                    fieldnames = ['evaluation_id', 'task_name', 'equipment_system',
                                  'complexity_level', 'recommended_role', 'overall_score',
                                  'evaluation_date', 'evaluator_name']
                    writer = csv.DictWriter(output, fieldnames=fieldnames)
                    writer.writeheader()

                    for eval in evaluations:
                        writer.writerow({
                            'evaluation_id': eval['evaluation_id'],
                            'task_name': eval['task_name'],
                            'equipment_system': eval['equipment_system'],
                            'complexity_level': eval['complexity_level'],
                            'recommended_role': eval['recommended_role'],
                            'overall_score': eval['overall_score'],
                            'evaluation_date': eval['evaluation_date'],
                            'evaluator_name': eval['evaluator_name']
                        })

                return {
                    'success': True,
                    'data': output.getvalue(),
                    'format': 'csv'
                }
            else:
                return {
                    'success': False,
                    'message': 'Unsupported format. Use json or csv.'
                }

        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'message': f'Error exporting evaluations: {str(e)}'
            }


# =====================================================
# SIMPLE WEB API (optional - using Flask)
# =====================================================

def create_simple_api():
    """Create a simple Flask API for the evaluation system"""

    try:
        from flask import Flask, request, jsonify, send_from_directory
        from flask_cors import CORS
        import os

        app = Flask(__name__)
        CORS(app)  # Enable CORS for web form integration

        # Initialize evaluation manager
        eval_manager = TaskEvaluationManager()

        @app.route('/api/evaluations', methods=['POST'])
        def save_evaluation():
            """Save a new evaluation"""
            try:
                data = request.get_json()
                result = eval_manager.save_form_data(data)
                return jsonify(result)
            except Exception as e:
                return jsonify({
                    'success': False,
                    'error': str(e)
                }), 500

        @app.route('/api/evaluations/<int:evaluation_id>', methods=['GET'])
        def get_evaluation(evaluation_id):
            """Get evaluation by ID"""
            try:
                result = eval_manager.get_evaluation_summary(evaluation_id)
                return jsonify(result)
            except Exception as e:
                return jsonify({
                    'success': False,
                    'error': str(e)
                }), 500

        @app.route('/api/evaluations', methods=['GET'])
        def list_evaluations():
            """List all evaluations or search"""
            try:
                search_term = request.args.get('search')
                complexity_level = request.args.get('complexity_level')
                disciplines = request.args.getlist('disciplines')

                if search_term or complexity_level or disciplines:
                    result = eval_manager.search_evaluations(
                        search_term=search_term,
                        complexity_level=int(complexity_level) if complexity_level else None,
                        disciplines=disciplines if disciplines else None
                    )
                else:
                    result = eval_manager.get_all_evaluations()

                return jsonify(result)
            except Exception as e:
                return jsonify({
                    'success': False,
                    'error': str(e)
                }), 500

        @app.route('/api/statistics', methods=['GET'])
        def get_statistics():
            """Get evaluation statistics"""
            try:
                result = eval_manager.get_statistics()
                return jsonify(result)
            except Exception as e:
                return jsonify({
                    'success': False,
                    'error': str(e)
                }), 500

        @app.route('/api/export', methods=['GET'])
        def export_evaluations():
            """Export evaluations"""
            try:
                format_type = request.args.get('format', 'json')
                result = eval_manager.export_evaluations(format_type)
                return jsonify(result)
            except Exception as e:
                return jsonify({
                    'success': False,
                    'error': str(e)
                }), 500

        # ---------- HTML SERVING ROUTES (must be BEFORE return app) ----------
        @app.route('/')
        def serve_root():
            # Serves the HTML file at http://localhost:5000/
            return send_from_directory(os.path.dirname(os.path.abspath(__file__)), 'task_evaul.html')

        @app.route('/task_evaul.html')
        def serve_html():
            # Also accessible at http://localhost:5000/task_evaul.html
            return send_from_directory(os.path.dirname(os.path.abspath(__file__)), 'task_evaul.html')

        return app

    except ImportError:
        print("Flask not installed. Install with: pip install flask flask-cors")
        return None

# =====================================================
# COMMAND LINE INTERFACE
# =====================================================

def create_cli():
    """Create a simple command line interface"""
    import argparse

    parser = argparse.ArgumentParser(description='Task Evaluation Database Manager')
    parser.add_argument('--action', choices=['list', 'search', 'get', 'stats', 'export'],
                        required=True, help='Action to perform')
    parser.add_argument('--id', type=int, help='Evaluation ID for get action')
    parser.add_argument('--search', help='Search term for search action')
    parser.add_argument('--complexity', type=int, choices=[1, 2, 3, 4],
                        help='Complexity level filter')
    parser.add_argument('--format', choices=['json', 'csv'], default='json',
                        help='Export format')

    args = parser.parse_args()

    # Initialize manager
    eval_manager = TaskEvaluationManager()

    if args.action == 'list':
        result = eval_manager.get_all_evaluations()
        print(json.dumps(result, indent=2, default=str))

    elif args.action == 'search':
        result = eval_manager.search_evaluations(
            search_term=args.search,
            complexity_level=args.complexity
        )
        print(json.dumps(result, indent=2, default=str))

    elif args.action == 'get':
        if not args.id:
            print("Error: --id required for get action")
            return
        result = eval_manager.get_evaluation_summary(args.id)
        print(json.dumps(result, indent=2, default=str))

    elif args.action == 'stats':
        result = eval_manager.get_statistics()
        print(json.dumps(result, indent=2, default=str))

    elif args.action == 'export':
        result = eval_manager.export_evaluations(args.format)
        if result['success']:
            filename = f"evaluations_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.{args.format}"
            with open(filename, 'w') as f:
                if args.format == 'json':
                    json.dump(result['data'], f, indent=2, default=str)
                else:
                    f.write(result['data'])
            print(f"Exported to {filename}")
        else:
            print(f"Export failed: {result['message']}")


# =====================================================
# EXAMPLE USAGE AND TESTING
# =====================================================

def test_integration():
    """Test the integration with sample data"""

    # Initialize manager
    eval_manager = TaskEvaluationManager()

    # Sample form data (as it would come from your evaluation form)
    sample_form_data = {
        'taskName': 'Operate Station 1 in Manual Mode',
        'taskDescription': 'Operate Bag Maker Station 1 in manual mode for setup and troubleshooting',
        'equipment': 'Bag Maker Station 1',
        'location': 'Production Floor A',
        'disciplines': ['operations'],  # Updated to match HTML form values
        'modifiers': [],
        'technical': '1',
        'problem': '1',
        'decision': '1',
        'impact': '2',
        'supervision': '1',
        'tools': '1',
        'prerequisites': 'Basic understanding of bag making process',
        'safetyConsiderations': 'Standard lockout/tagout procedures',
        'tools_required': 'Standard hand tools, basic meters',
        'estimatedTime': '30 minutes',
        'frequency': 'As-Needed',
        'successCriteria': 'Station operates in manual mode without errors',
        'qualityStandards': 'Follow all SOP procedures',
        'evaluatorName': 'John Smith',
        'evaluationNotes': 'Basic operational task suitable for entry-level personnel'
    }

    # Save the evaluation
    print("Saving evaluation...")
    save_result = eval_manager.save_form_data(sample_form_data)
    print(f"Save result: {save_result}")

    if save_result['success']:
        eval_id = save_result['evaluation_id']

        # Retrieve the evaluation
        print(f"\nRetrieving evaluation {eval_id}...")
        get_result = eval_manager.get_evaluation_summary(eval_id)
        if get_result['success']:
            evaluation = get_result['data']
            print(f"Task: {evaluation['task_name']}")
            print(f"Complexity Level: {evaluation['results']['complexity_level']}")
            print(f"Recommended Role: {evaluation['results']['recommended_role']}")
            print(f"Overall Score: {evaluation['results']['overall_score']}")

        # Get statistics
        print("\nGetting statistics...")
        stats_result = eval_manager.get_statistics()
        if stats_result['success']:
            stats = stats_result['data']
            print(f"Total evaluations: {stats['total_evaluations']}")
            print(f"Complexity distribution: {stats['complexity_distribution']}")

        # Search evaluations
        print("\nSearching evaluations...")
        search_result = eval_manager.search_evaluations(search_term="Station")
        if search_result['success']:
            print(f"Found {search_result['count']} evaluations matching 'Station'")

    # Test with more sample data
    additional_samples = [
        {
            'taskName': 'Align Station Dies',
            'taskDescription': 'Align station dies to specifications and make timing adjustments',
            'equipment': 'Bag Maker Station 2',
            'location': 'Production Floor A',
            'disciplines': ['mechanical', 'electrical'],
            'modifiers': [],
            'technical': '2',
            'problem': '2',
            'decision': '2',
            'impact': '3',
            'supervision': '2',
            'tools': '2',
            'evaluatorName': 'Mary Wilson',
            'evaluationNotes': 'Requires mechanical and electrical knowledge'
        },
        {
            'taskName': 'Program PLC Logic',
            'taskDescription': 'Modify PLC program areas via T-CAM system',
            'equipment': 'Control System',
            'location': 'Control Room',
            'disciplines': ['controls'],
            'modifiers': [],
            'technical': '3',
            'problem': '3',
            'decision': '3',
            'impact': '4',
            'supervision': '3',
            'tools': '3',
            'evaluatorName': 'Bob Brown',
            'evaluationNotes': 'Advanced programming task requiring expertise'
        }
    ]

    print("\nAdding additional sample evaluations...")
    for sample in additional_samples:
        result = eval_manager.save_form_data(sample)
        if result['success']:
            print(f"Saved: {sample['taskName']} (ID: {result['evaluation_id']})")

    # Final statistics
    print("\nFinal statistics:")
    final_stats = eval_manager.get_statistics()
    if final_stats['success']:
        stats = final_stats['data']
        print(f"Total evaluations: {stats['total_evaluations']}")
        print("Complexity distribution:")
        for level, count in stats['complexity_distribution'].items():
            print(f"  {level}: {count}")
        print("Average scores:")
        for criteria, score in stats['average_scores'].items():
            print(f"  {criteria}: {score:.2f}")


# =====================================================
# MAIN EXECUTION
# =====================================================

if __name__ == "__main__":
    import sys

    USAGE = """\
Usage: python form_evaul.py [test|report|cli|api]
  test    - Run integration tests (creates/test database)
  report  - Generate and print a summary report to the terminal
  cli     - Start a command line interface for ad hoc queries
  api     - Start the web API server (Flask) with HTML form at /
"""

    if len(sys.argv) > 1:
        cmd = sys.argv[1].lower()
        if cmd == 'test':
            test_integration()
        elif cmd == 'report':
            eval_manager = TaskEvaluationManager()
            all_evals = eval_manager.get_all_evaluations()
            if not all_evals['success']:
                print("Error getting evaluations")
                sys.exit(1)

            evaluations = all_evals['data']
            stats = eval_manager.get_statistics()
            if not stats['success']:
                print("Error getting statistics")
                sys.exit(1)
            stats_data = stats['data']

            # Generate report
            report = f"""
TASK EVALUATION SUMMARY REPORT
Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

OVERVIEW
========
Total Evaluations: {stats_data['total_evaluations']}

COMPLEXITY DISTRIBUTION
=======================
Level 1 (Mechanic I): {stats_data['complexity_distribution']['level_1']}
Level 2 (Mechanic II): {stats_data['complexity_distribution']['level_2']}
Level 3 (Mechanic III): {stats_data['complexity_distribution']['level_3']}
Level 4 (Maintenance Technician): {stats_data['complexity_distribution']['level_4']}

AVERAGE SCORES BY CRITERIA
==========================
Technical Knowledge: {stats_data['average_scores']['technical']:.2f}
Problem Solving: {stats_data['average_scores']['problem']:.2f}
Decision Making: {stats_data['average_scores']['decision']:.2f}
Impact of Errors: {stats_data['average_scores']['impact']:.2f}
Supervision Required: {stats_data['average_scores']['supervision']:.2f}
Tools & Equipment: {stats_data['average_scores']['tools']:.2f}

RECENT EVALUATIONS
==================
"""
            recent_evals = evaluations[:10]
            for eval in recent_evals:
                report += f"""
Task: {eval['task_name']}
Equipment: {eval['equipment_system'] or 'N/A'}
Complexity: Level {eval['complexity_level']} ({eval['recommended_role']})
Score: {eval['overall_score']:.2f}
Evaluated: {eval['evaluation_date']}
Evaluator: {eval['evaluator_name']}
---
"""
            print(report)

        elif cmd == 'cli':
            create_cli()
        elif cmd == 'api':
            app = create_simple_api()
            if app:
                print("\nStarting API server...")
                print("You can access your form at: http://localhost:5000/")
                print("Press CTRL+C to quit.")
                app.run(debug=True, host='0.0.0.0', port=5000)
            else:
                print("Flask not available. Install with: pip install flask flask-cors")
        else:
            print(f"Unknown command: {cmd}\n")
            print(USAGE)
    else:
        print(USAGE)
