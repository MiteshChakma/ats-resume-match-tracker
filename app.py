from flask import Flask, render_template, request, jsonify, redirect, url_for
from sqlalchemy import or_
from datetime import datetime, timedelta
import json

from config import Config
from database.db import db
from database.models import JobAnalysis, DiscoveredKeyword
from services.scorer import ATSScorer
from services.jd_parser import JDParser
from services.resume_parser import ResumeParser
from services.resume_extractor import ResumeExtractor
from services.resume_normalizer import ResumeNormalizer
from services.llm_suggester import LLMSuggester


app = Flask(__name__)
app.config.from_object(Config)

db.init_app(app)

with app.app_context():
    db.create_all()


def parse_bool(value, default=False):
    if value is None:
        return default
    return str(value).strip().lower() in {'true', '1', 'yes', 'on'}


def to_json_text(value):
    try:
        return json.dumps(value or {}, ensure_ascii=False)
    except Exception:
        return json.dumps({}, ensure_ascii=False)


def from_json_text(value, default=None):
    if not value:
        return default
    try:
        return json.loads(value)
    except Exception:
        return default


def csv_join(values):
    if not values:
        return ''
    return ','.join(str(v).strip() for v in values if str(v).strip())


def get_resume_text_and_filename():
    resume_text = request.form.get('resumeText', '').strip()
    extracted_resume_text = request.form.get('extractedResumeText', '').strip()
    resume_filename = request.form.get('resumeFileName', '').strip()

    if resume_text:
        normalized = ResumeNormalizer.normalize(resume_text)
        return normalized, (resume_filename or 'pasted_resume.txt'), None

    if extracted_resume_text:
        normalized = ResumeNormalizer.normalize(extracted_resume_text)
        return normalized, (resume_filename or 'extracted_resume.txt'), None

    resume_file = request.files.get('resumeFile')
    if resume_file:
        filename = (resume_file.filename or '').strip()

        if not filename:
            return None, None, (
                jsonify({'status': 'error', 'message': 'Uploaded resume file must have a filename.'}),
                400
            )

        lower_name = filename.lower()

        try:
            if lower_name.endswith('.pdf'):
                raw_resume_text = ResumeExtractor.extract_text_from_pdf(resume_file)
            elif lower_name.endswith('.docx') and hasattr(ResumeExtractor, 'extract_text_from_docx'):
                raw_resume_text = ResumeExtractor.extract_text_from_docx(resume_file)
            else:
                return None, None, (
                    jsonify({
                        'status': 'error',
                        'message': 'Provide resumeText/extractedResumeText, or upload a supported resume file.'
                    }),
                    400
                )

            normalized = ResumeNormalizer.normalize(raw_resume_text)

            if not normalized.strip():
                return None, None, (
                    jsonify({'status': 'error', 'message': 'Could not extract text from the uploaded resume file.'}),
                    400
                )

            return normalized, (resume_filename or filename), None

        except Exception as exc:
            return None, None, (
                jsonify({'status': 'error', 'message': f'Failed to process uploaded resume file: {str(exc)}'}),
                400
            )

    return None, None, (
        jsonify({
            'status': 'error',
            'message': 'resumeText or extractedResumeText is required. Optional file upload can be used if supported.'
        }),
        400
    )


def save_discovered_keywords(job_analysis_id, candidate_keywords, source_text):
    DiscoveredKeyword.query.filter_by(job_analysis_id=job_analysis_id).delete()

    for term in candidate_keywords or []:
        db.session.add(DiscoveredKeyword(
            job_analysis_id=job_analysis_id,
            term=term,
            source_type='jd',
            frequency=1,
            context=source_text[:500] if source_text else None,
            is_promoted=False
        ))


def hydrate_analysis_fields(analysis, scoring_result, jd_parsed, resume_parsed, resume_filename, resume_text):
    analysis.resume_filename = resume_filename
    analysis.resume_text = resume_text
    analysis.ats_score = scoring_result['overall_score']

    analysis.matched_skills = csv_join(scoring_result.get('matched_skills', []))
    analysis.missing_skills = csv_join(scoring_result.get('missing_skills', []))

    analysis.parsed_known_skills = csv_join(jd_parsed.get('known_skills', []))
    analysis.parsed_candidate_keywords = csv_join(jd_parsed.get('candidate_keywords', []))
    analysis.parsed_experience_years = jd_parsed.get('experience_years')
    analysis.parsed_role_level = jd_parsed.get('role_level')

    analysis.parsed_resume_known_skills = csv_join(resume_parsed.get('known_skills', []))
    analysis.parsed_resume_candidate_keywords = csv_join(resume_parsed.get('candidate_keywords', []))
    analysis.parsed_resume_experience_years = resume_parsed.get('experience_years')
    analysis.parsed_resume_role_level = resume_parsed.get('role_level')
    analysis.parsed_resume_job_titles = csv_join(resume_parsed.get('job_titles', []))

    if hasattr(analysis, 'jd_parsed_json'):
        analysis.jd_parsed_json = to_json_text(jd_parsed)

    if hasattr(analysis, 'resume_parsed_json'):
        analysis.resume_parsed_json = to_json_text(resume_parsed)

    if hasattr(analysis, 'scoring_result_json'):
        analysis.scoring_result_json = to_json_text(scoring_result)


def build_analyze_response(status, message, analysis, scoring_result, jd_parsed, resume_parsed, resume_text):
    return jsonify({
        'status': status,
        'message': message,
        'analysis_id': analysis.id,
        'score': scoring_result['overall_score'],
        'breakdown': scoring_result.get('breakdown', {}),
        'matched_skills': scoring_result.get('matched_skills', []),
        'missing_skills': scoring_result.get('missing_skills', []),
        'matched_candidate_keywords': scoring_result.get('matched_candidate_keywords', []),
        'missing_candidate_keywords': scoring_result.get('missing_candidate_keywords', []),
        'experience_gap': scoring_result.get('experience_gap'),
        'experience_status': scoring_result.get('experience_status'),
        'role_level_status': scoring_result.get('role_level_status'),
        'iteration_count': analysis.iteration_count,
        'job_title': analysis.job_title,
        'company_name': analysis.company_name,
        'source_platform': analysis.source_platform,
        'resume_filename': analysis.resume_filename,
        'is_applied': analysis.is_applied,
        'created_at': (
            analysis.updated_at.strftime('%Y-%m-%d %H:%M:%S')
            if status == 'updated'
            else analysis.created_at.strftime('%Y-%m-%d %H:%M:%S')
        ),
        'jd_parsed': {
            'known_skills': jd_parsed.get('known_skills', []),
            'candidate_keywords': jd_parsed.get('candidate_keywords', []),
            'experience_years': jd_parsed.get('experience_years'),
            'role_level': jd_parsed.get('role_level')
        },
        'resume_parsed': {
            'known_skills': resume_parsed.get('known_skills', []),
            'candidate_keywords': resume_parsed.get('candidate_keywords', []),
            'experience_years': resume_parsed.get('experience_years'),
            'role_level': resume_parsed.get('role_level'),
            'job_titles': resume_parsed.get('job_titles', []),
            'experience_entries': resume_parsed.get('experience_entries', {}),
            'sections': resume_parsed.get('sections', {})
        },
        'resume_text_preview': resume_text[:1500]
    })


def get_jobs_table_data(status_filter=None, page_title='Jobs'):
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 10, type=int)
    search = request.args.get('search', '').strip()
    start_date = request.args.get('start_date', '').strip()
    end_date = request.args.get('end_date', '').strip()

    if per_page not in [5, 10, 25, 50, 100]:
        per_page = 10

    query = JobAnalysis.query

    if status_filter == 'applied':
        query = query.filter_by(is_applied=True)
    elif status_filter == 'analyzed':
        query = query.filter_by(is_applied=False)

    if search:
        like_value = f"%{search}%"
        query = query.filter(
            or_(
                JobAnalysis.job_title.ilike(like_value),
                JobAnalysis.company_name.ilike(like_value),
                JobAnalysis.source_platform.ilike(like_value),
                JobAnalysis.resume_filename.ilike(like_value)
            )
        )

    if start_date:
        try:
            start_dt = datetime.strptime(start_date, '%Y-%m-%d')
            query = query.filter(JobAnalysis.updated_at >= start_dt)
        except ValueError:
            start_date = ''

    if end_date:
        try:
            end_dt = datetime.strptime(end_date, '%Y-%m-%d') + timedelta(days=1)
            query = query.filter(JobAnalysis.updated_at < end_dt)
        except ValueError:
            end_date = ''

    pagination = query.order_by(JobAnalysis.updated_at.desc()).paginate(
        page=page,
        per_page=per_page,
        error_out=False
    )

    return render_template(
        'jobs.html',
        analyses=pagination.items,
        pagination=pagination,
        page_title=page_title,
        status_filter=status_filter,
        per_page=per_page,
        search=search,
        start_date=start_date,
        end_date=end_date
    )


@app.route('/')
def home():
    return render_template('index.html')


@app.route('/analyze', methods=['POST'])
def analyze():
    job_title = request.form.get('jobTitle', '').strip()
    company_name = request.form.get('companyName', '').strip()
    job_url = request.form.get('jobUrl', '').strip()
    source_platform = request.form.get('sourcePlatform', '').strip()
    job_description = request.form.get('jobDescription', '').strip()
    is_applied = parse_bool(request.form.get('isApplied'), default=False)

    if not job_title:
        return jsonify({'status': 'error', 'message': 'jobTitle is required.'}), 400
    if not company_name:
        return jsonify({'status': 'error', 'message': 'companyName is required.'}), 400
    if not job_url:
        return jsonify({'status': 'error', 'message': 'jobUrl is required.'}), 400
    if not job_description:
        return jsonify({'status': 'error', 'message': 'jobDescription is required.'}), 400
    if not source_platform:
        return jsonify({'status': 'error', 'message': 'sourcePlatform is required.'}), 400

    resume_text, resume_filename, resume_error = get_resume_text_and_filename()
    if resume_error:
        return resume_error

    resume_parsed = ResumeParser.parse(resume_text)
    jd_parsed = JDParser.parse(job_description)

    scoring_result = ATSScorer.score(
        resume_parsed=resume_parsed,
        jd_parsed=jd_parsed,
        jd_title=job_title
    )

    existing = JobAnalysis.query.filter_by(
        resume_filename=resume_filename,
        job_url=job_url
    ).first()

    if existing:
        if existing.is_applied:
            return jsonify({
                'status': 'locked',
                'message': 'This job has already been marked as applied and cannot be modified.'
            }), 409

        existing.job_title = job_title
        existing.company_name = company_name
        existing.job_url = job_url
        existing.source_platform = source_platform
        existing.job_description = job_description
        existing.iteration_count += 1
        existing.is_applied = is_applied

        hydrate_analysis_fields(existing, scoring_result, jd_parsed, resume_parsed, resume_filename, resume_text)
        db.session.commit()

        save_discovered_keywords(existing.id, jd_parsed.get('candidate_keywords', []), job_description)
        db.session.commit()

        return build_analyze_response(
            'updated',
            'Existing analysis updated successfully',
            existing,
            scoring_result,
            jd_parsed,
            resume_parsed,
            resume_text
        )

    new_analysis = JobAnalysis(
        job_title=job_title,
        company_name=company_name,
        job_url=job_url,
        source_platform=source_platform,
        job_description=job_description,
        resume_filename=resume_filename,
        iteration_count=1,
        is_applied=is_applied
    )

    hydrate_analysis_fields(new_analysis, scoring_result, jd_parsed, resume_parsed, resume_filename, resume_text)

    db.session.add(new_analysis)
    db.session.commit()

    save_discovered_keywords(new_analysis.id, jd_parsed.get('candidate_keywords', []), job_description)
    db.session.commit()

    return build_analyze_response(
        'created',
        'New analysis created successfully',
        new_analysis,
        scoring_result,
        jd_parsed,
        resume_parsed,
        resume_text
    )


@app.route('/history', methods=['GET'])
def history():
    analyses = JobAnalysis.query.order_by(JobAnalysis.updated_at.desc()).all()

    return jsonify([
        {
            'id': item.id,
            'job_title': item.job_title,
            'company_name': item.company_name,
            'source_platform': item.source_platform,
            'ats_score': item.ats_score,
            'iteration_count': item.iteration_count,
            'is_applied': item.is_applied,
            'resume_filename': item.resume_filename,
            'created_at': item.created_at.strftime('%Y-%m-%d %H:%M:%S'),
            'updated_at': item.updated_at.strftime('%Y-%m-%d %H:%M:%S')
        }
        for item in analyses
    ])


@app.route('/debug/db')
def debug_db():
    rows = JobAnalysis.query.all()

    return {
        "count": len(rows),
        "data": [
            {
                "id": r.id,
                "job_title": r.job_title,
                "company_name": r.company_name,
                "job_url": r.job_url,
                "source_platform": r.source_platform,
                "resume_filename": r.resume_filename,
                "resume_text_preview": r.resume_text[:500] if getattr(r, 'resume_text', None) else None,
                "ats_score": r.ats_score,
                "matched_skills": r.matched_skills,
                "missing_skills": r.missing_skills,
                "parsed_known_skills": r.parsed_known_skills,
                "parsed_candidate_keywords": r.parsed_candidate_keywords,
                "parsed_resume_known_skills": r.parsed_resume_known_skills,
                "parsed_resume_candidate_keywords": r.parsed_resume_candidate_keywords,
                "current_suggestions_json": getattr(r, 'current_suggestions_json', None),
                "current_suggestions_generated_at": str(r.current_suggestions_generated_at)
                    if getattr(r, 'current_suggestions_generated_at', None) else None,
                "applied_suggestions_json": getattr(r, 'applied_suggestions_json', None),
                "applied_suggestions_saved_at": str(r.applied_suggestions_saved_at)
                    if getattr(r, 'applied_suggestions_saved_at', None) else None,
                "iteration_count": r.iteration_count,
                "is_applied": r.is_applied,
                "created_at": str(r.created_at),
                "updated_at": str(r.updated_at)
            }
            for r in rows
        ]
    }


@app.route('/test-jd')
def test_jd():
    sample_jd = """
    Looking for a Senior Python Developer with 5+ years experience.
    Must have experience with AWS, Docker, APIs and Machine Learning.
    Should be comfortable with language models, automation solutions,
    production deployment, and cross-functional collaboration.
    """
    return jsonify(JDParser.parse(sample_jd))


@app.route('/test-resume')
def test_resume():
    sample_resume = """
    PROFESSIONAL SUMMARY
    Senior Data Analyst with 5 years of experience in Python, SQL, AWS, APIs, and Docker.

    SKILLS
    Python, SQL, AWS, Docker, Tableau, Power BI, APIs

    EXPERIENCE
    Senior Data Analyst
    ABC Company
    Jan 2021 - Mar 2023
    Built automation workflows and dashboard development solutions.
    Worked with cross-functional collaboration, reporting automation, and data visualization.

    Data Analyst
    XYZ Company
    Jun 2019 - Dec 2020
    Designed data pipelines and implemented cloud infrastructure improvements.
    """

    sample_jd = """
    Looking for a Senior Python Developer with 5+ years experience.
    Must have experience with AWS, Docker, APIs, SQL and Machine Learning.
    Should be comfortable with automation, data visualization,
    cross-functional collaboration, and cloud infrastructure.
    """

    resume_parsed = ResumeParser.parse(sample_resume)
    jd_parsed = JDParser.parse(sample_jd)

    scoring_result = ATSScorer.score(
        resume_parsed=resume_parsed,
        jd_parsed=jd_parsed,
        jd_title='Senior Python Developer'
    )

    suggestions = LLMSuggester.generate_dual(
        resume_text=sample_resume,
        job_description=sample_jd,
        resume_parsed=resume_parsed,
        jd_parsed=jd_parsed,
        scoring_result=scoring_result
    )

    return jsonify({
        'resume_parsed': resume_parsed,
        'jd_parsed': jd_parsed,
        'scoring_result': scoring_result,
        'suggestions': suggestions
    })


@app.route('/jobs')
def all_jobs():
    return get_jobs_table_data(status_filter=None, page_title='All Jobs')


@app.route('/jobs/analyzed')
def analyzed_jobs():
    return get_jobs_table_data(status_filter='analyzed', page_title='Analyzed Jobs')


@app.route('/jobs/applied')
def applied_jobs():
    return get_jobs_table_data(status_filter='applied', page_title='Applied Jobs')


@app.route('/jobs/<int:job_id>')
def job_detail(job_id):
    analysis = JobAnalysis.query.get_or_404(job_id)

    current_suggestions = from_json_text(
        getattr(analysis, 'current_suggestions_json', None),
        default=None
    )

    applied_suggestions = from_json_text(
        getattr(analysis, 'applied_suggestions_json', None),
        default=None
    )

    return render_template(
        'job_detail.html',
        analysis=analysis,
        current_suggestions=current_suggestions,
        applied_suggestions=applied_suggestions
    )


@app.route('/jobs/<int:job_id>/toggle-applied', methods=['POST'])
def toggle_applied(job_id):
    analysis = JobAnalysis.query.get_or_404(job_id)

    if not analysis.is_applied:
        if not getattr(analysis, 'current_suggestions_json', None):
            return jsonify({
                'status': 'error',
                'message': 'Generate AI suggestions before marking this job as applied.'
            }), 400

        analysis.is_applied = True
        analysis.applied_suggestions_json = analysis.current_suggestions_json
        analysis.applied_suggestions_saved_at = datetime.utcnow()
    else:
        analysis.is_applied = False

    db.session.commit()

    return redirect(url_for('job_detail', job_id=job_id))


@app.route('/jobs/<int:job_id>/generate-suggestions', methods=['POST'])
def generate_job_suggestions(job_id):
    analysis = JobAnalysis.query.get_or_404(job_id)

    resume_text = (analysis.resume_text or '').strip()
    job_description = (analysis.job_description or '').strip()
    job_title = (analysis.job_title or '').strip()

    if not resume_text:
        return jsonify({
            'status': 'error',
            'message': 'No saved resume text found for this analysis. Re-run analyze with resume text before generating suggestions.'
        }), 400

    if analysis.is_applied:
        return jsonify({
            'status': 'locked',
            'message': 'This job is already marked as applied. Suggestions are frozen for applied jobs.'
        }), 409

    resume_parsed = ResumeParser.parse(resume_text)
    jd_parsed = JDParser.parse(job_description)

    scoring_result = ATSScorer.score(
        resume_parsed=resume_parsed,
        jd_parsed=jd_parsed,
        jd_title=job_title
    )

    combined_suggestions = LLMSuggester.generate_dual(
        resume_text=resume_text,
        job_description=job_description,
        resume_parsed=resume_parsed,
        jd_parsed=jd_parsed,
        scoring_result=scoring_result
    )

    analysis.current_suggestions_json = to_json_text(combined_suggestions)
    analysis.current_suggestions_generated_at = datetime.utcnow()
    db.session.commit()

    return redirect(url_for('job_detail', job_id=job_id))

@app.route('/debug/resume/<int:job_id>')
def debug_resume(job_id):
    analysis = JobAnalysis.query.get_or_404(job_id)

    return jsonify({
        "id": analysis.id,
        "resume_filename": analysis.resume_filename,
        "resume_text_length": len(analysis.resume_text) if analysis.resume_text else 0,
        "resume_text": analysis.resume_text
    })

if __name__ == '__main__':
    app.run(debug=True)