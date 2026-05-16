from datetime import datetime
from database.db import db


class JobAnalysis(db.Model):
    __tablename__ = 'job_analysis'

    id = db.Column(db.Integer, primary_key=True)

    job_title = db.Column(db.String(255), nullable=False)
    company_name = db.Column(db.String(255), nullable=False)
    job_url = db.Column(db.Text, nullable=True)
    source_platform = db.Column(db.String(100), nullable=False)
    job_description = db.Column(db.Text, nullable=False)
    resume_filename = db.Column(db.String(255), nullable=False)

    # Store extracted/plain resume text used for parsing/scoring
    resume_text = db.Column(db.Text, nullable=True)

    iteration_count = db.Column(db.Integer, default=1)
    is_applied = db.Column(db.Boolean, default=False)

    ats_score = db.Column(db.Integer, default=0)
    matched_skills = db.Column(db.Text, nullable=True)
    missing_skills = db.Column(db.Text, nullable=True)

    parsed_known_skills = db.Column(db.Text, nullable=True)
    parsed_candidate_keywords = db.Column(db.Text, nullable=True)
    parsed_experience_years = db.Column(db.Integer, nullable=True)
    parsed_role_level = db.Column(db.String(50), nullable=True)

    parsed_resume_known_skills = db.Column(db.Text, nullable=True)
    parsed_resume_candidate_keywords = db.Column(db.Text, nullable=True)
    parsed_resume_experience_years = db.Column(db.Integer, nullable=True)
    parsed_resume_role_level = db.Column(db.String(50), nullable=True)
    parsed_resume_job_titles = db.Column(db.Text, nullable=True)

    current_suggestions_json = db.Column(db.Text, nullable=True)
    current_suggestions_generated_at = db.Column(db.DateTime, nullable=True)

    applied_suggestions_json = db.Column(db.Text, nullable=True)
    applied_suggestions_saved_at = db.Column(db.DateTime, nullable=True)

    # Saved AI suggestions per job
    ai_suggestions_json = db.Column(db.Text, nullable=True)
    ai_suggestions_generated_at = db.Column(db.DateTime, nullable=True)

    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(
        db.DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow
    )

    discovered_keywords = db.relationship(
        'DiscoveredKeyword',
        backref='job_analysis',
        lazy=True,
        cascade='all, delete-orphan'
    )


class DiscoveredKeyword(db.Model):
    __tablename__ = 'discovered_keywords'

    id = db.Column(db.Integer, primary_key=True)

    job_analysis_id = db.Column(
        db.Integer,
        db.ForeignKey('job_analysis.id'),
        nullable=False
    )

    term = db.Column(db.String(255), nullable=False)
    source_type = db.Column(db.String(50), default='jd')
    frequency = db.Column(db.Integer, default=1)
    context = db.Column(db.Text, nullable=True)
    is_promoted = db.Column(db.Boolean, default=False)

    created_at = db.Column(db.DateTime, default=datetime.utcnow)