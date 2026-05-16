console.log('CLEAN ATS APP.JS LOADED');

document.addEventListener('DOMContentLoaded', function () {
    const analyzeBtn = document.getElementById('analyzeBtn');
    const resultBox = document.getElementById('analysisResults');
    const statusBadge = document.getElementById('resultStatusBadge');

    if (!analyzeBtn || !resultBox || !statusBadge) {
        return;
    }

    function escapeHtml(value) {
        return String(value ?? '')
            .replaceAll('&', '&amp;')
            .replaceAll('<', '&lt;')
            .replaceAll('>', '&gt;')
            .replaceAll('"', '&quot;')
            .replaceAll("'", '&#039;');
    }

    function renderList(items, className = '') {
        if (!Array.isArray(items) || items.length === 0) {
            return `<p class="results-empty">None found.</p>`;
        }

        return items
            .map(item => `<span class="skill-chip ${className}">${escapeHtml(item)}</span>`)
            .join('');
    }

    function scoreClass(score) {
        if (score >= 75) return 'score-high';
        if (score >= 50) return 'score-mid';
        return 'score-low';
    }

    function renderAnalysisResult(data) {
        statusBadge.textContent = data.status || 'Analyzed';
        statusBadge.className = 'status-pill success';

        resultBox.className = '';

        resultBox.innerHTML = `
            <div class="result-grid">
                <div class="result-section">
                    <h3>Score Summary</h3>
                    <div class="score-big ${scoreClass(data.score)}">${escapeHtml(data.score)}%</div>
                    <div class="meta-row"><span class="meta-label">Status:</span> ${escapeHtml(data.status)}</div>
                    <div class="meta-row"><span class="meta-label">Message:</span> ${escapeHtml(data.message)}</div>
                    <div class="meta-row"><span class="meta-label">Iteration:</span> ${escapeHtml(data.iteration_count)}</div>
                </div>

                <div class="result-section">
                    <h3>Fit Signals</h3>
                    <div class="meta-row"><span class="meta-label">Experience:</span> ${escapeHtml(data.experience_status || 'N/A')}</div>
                    <div class="meta-row"><span class="meta-label">Experience Gap:</span> ${escapeHtml(data.experience_gap ?? 'N/A')}</div>
                    <div class="meta-row"><span class="meta-label">Role Alignment:</span> ${escapeHtml(data.role_level_status || 'N/A')}</div>
                </div>

                <div class="result-section full-width">
                    <h3>Score Breakdown</h3>
                    <div class="result-grid">
                        <div class="meta-row"><span class="meta-label">Skills:</span> ${escapeHtml(data.breakdown?.skills_score ?? 0)}</div>
                        <div class="meta-row"><span class="meta-label">Keywords:</span> ${escapeHtml(data.breakdown?.candidate_keyword_score ?? 0)}</div>
                        <div class="meta-row"><span class="meta-label">Experience:</span> ${escapeHtml(data.breakdown?.experience_score ?? 0)}</div>
                        <div class="meta-row"><span class="meta-label">Role Level:</span> ${escapeHtml(data.breakdown?.role_level_score ?? 0)}</div>
                    </div>
                </div>

                <div class="result-section">
                    <h3>Matched Skills</h3>
                    ${renderList(data.matched_skills)}
                </div>

                <div class="result-section">
                    <h3>Missing Skills</h3>
                    ${renderList(data.missing_skills, 'missing')}
                </div>

                <div class="result-section">
                    <h3>Matched JD Keywords</h3>
                    ${renderList(data.matched_candidate_keywords, 'keyword')}
                </div>

                <div class="result-section">
                    <h3>Missing JD Keywords</h3>
                    ${renderList(data.missing_candidate_keywords, 'missing')}
                </div>

                <div class="result-section">
                    <h3>Parsed Job Description</h3>
                    <div class="meta-row"><span class="meta-label">Role Level:</span> ${escapeHtml(data.jd_parsed?.role_level || 'N/A')}</div>
                    <div class="meta-row"><span class="meta-label">Experience Required:</span> ${escapeHtml(data.jd_parsed?.experience_years ?? 'Not detected')}</div>

                    <h4>Known Skills</h4>
                    ${renderList(data.jd_parsed?.known_skills)}

                    <h4>Candidate Keywords</h4>
                    ${renderList(data.jd_parsed?.candidate_keywords, 'keyword')}
                </div>

                <div class="result-section">
                    <h3>Parsed Resume</h3>
                    <div class="meta-row"><span class="meta-label">Role Level:</span> ${escapeHtml(data.resume_parsed?.role_level || 'N/A')}</div>
                    <div class="meta-row"><span class="meta-label">Experience Found:</span> ${escapeHtml(data.resume_parsed?.experience_years ?? 'Not detected')} years</div>

                    <h4>Resume Skills</h4>
                    ${renderList(data.resume_parsed?.known_skills)}

                    <h4>Resume Keywords</h4>
                    ${renderList(data.resume_parsed?.candidate_keywords, 'keyword')}
                </div>

                <div class="result-section full-width">
                    <h3>Resume Text Preview</h3>
                    <pre style="white-space: pre-wrap; max-height: 260px; overflow-y: auto;">${escapeHtml(data.resume_text_preview || 'No preview available.')}</pre>
                </div>
            </div>
        `;
    }

    analyzeBtn.addEventListener('click', async function () {
        const resumeFile = document.getElementById('resumeFile').files[0];
        const jobTitle = document.getElementById('jobTitle').value.trim();
        const companyName = document.getElementById('companyName').value.trim();
        const jobUrl = document.getElementById('jobUrl').value.trim();
        const sourcePlatform = document.getElementById('sourcePlatform').value;
        const jobDescription = document.getElementById('jobDescription').value.trim();
        const isApplied = document.getElementById('isApplied').checked;

        if (!resumeFile) {
            statusBadge.textContent = 'Validation Error';
            statusBadge.className = 'status-pill error';
            resultBox.innerHTML = `<p class="results-empty">Please upload a resume PDF before analyzing.</p>`;
            return;
        }

        if (!jobTitle || !companyName || !jobUrl || !jobDescription || !sourcePlatform) {
            statusBadge.textContent = 'Validation Error';
            statusBadge.className = 'status-pill error';
            resultBox.innerHTML = `<p class="results-empty">Please fill in all required fields before analyzing.</p>`;
            return;
        }

        const formData = new FormData();
        formData.append('resumeFile', resumeFile);
        formData.append('jobTitle', jobTitle);
        formData.append('companyName', companyName);
        formData.append('jobUrl', jobUrl);
        formData.append('sourcePlatform', sourcePlatform);
        formData.append('jobDescription', jobDescription);
        formData.append('isApplied', String(isApplied));

        statusBadge.textContent = 'Analyzing...';
        statusBadge.className = 'status-pill warning';
        resultBox.innerHTML = `<p class="results-empty">Running ATS analysis...</p>`;

        try {
            const response = await fetch('/analyze', {
                method: 'POST',
                body: formData
            });

            const data = await response.json();

            if (!response.ok) {
                statusBadge.textContent = 'Error';
                statusBadge.className = 'status-pill error';
                resultBox.innerHTML = `<p class="results-empty">${escapeHtml(data.message || 'Backend returned an error.')}</p>`;
                return;
            }

            if (data.status === 'locked') {
                statusBadge.textContent = 'Locked';
                statusBadge.className = 'status-pill warning';
                resultBox.innerHTML = `<p class="results-empty">${escapeHtml(data.message)}</p>`;
                return;
            }

            renderAnalysisResult(data);

        } catch (error) {
            statusBadge.textContent = 'Error';
            statusBadge.className = 'status-pill error';
            resultBox.innerHTML = `
                <p class="results-empty">Error connecting to backend.</p>
                <p class="results-empty">${escapeHtml(error.message)}</p>
            `;
        }
    });
});