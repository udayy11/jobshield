/**
 * JobShield AI — Generic DOM-based Job Information Extractor & In-Page Popup Assistant
 * Extracts job posting attributes and automatically displays an on-page risk popup widget.
 */

const BACKEND_URL = "http://127.0.0.1:8000";

function extractJobInformation() {
  const result = {
    title: "",
    company: "",
    description: "",
    requirements: "",
    salary: "",
    recruiter_email: "",
    application_link: window.location.href
  };

  // 1. Extract Job Title
  const titleSelectors = [
    "#job-title",
    "[data-automation-id='jobTitle']",
    ".job-title",
    ".top-card-layout__title",
    ".jobsearch-JobInfoHeader-title",
    "h1.title",
    "h1"
  ];
  for (const sel of titleSelectors) {
    const el = document.querySelector(sel);
    if (el && el.innerText.trim().length > 2) {
      result.title = el.innerText.trim();
      break;
    }
  }

  // 2. Extract Company Name
  const companySelectors = [
    "#company-name",
    ".company",
    "[data-automation-id='companyName']",
    ".topcard__org-name-link",
    ".jobsearch-CompanyInfoContainer",
    ".employer-name",
    "[class*='company']"
  ];
  for (const sel of companySelectors) {
    const el = document.querySelector(sel);
    if (el && el.innerText.trim().length > 1) {
      const text = el.innerText.trim().split("\n")[0];
      if (text.length < 100) {
        result.company = text;
        break;
      }
    }
  }

  // 3. Extract Salary / Compensation
  const salarySelectors = [
    "#job-salary",
    ".salary",
    "[data-automation-id='salary']",
    ".jobsearch-JobMetadataHeader-item",
    "[class*='salary']",
    "[class*='compensation']"
  ];
  for (const sel of salarySelectors) {
    const el = document.querySelector(sel);
    if (el && el.innerText.trim().length > 2) {
      result.salary = el.innerText.replace(/Compensation:\s*|Salary:\s*/i, "").trim().split("\n")[0];
      break;
    }
  }

  // 3b. Location
  const locEl = document.querySelector("#job-location, .location, [class*='location']");
  if (locEl) {
    result.location = locEl.innerText.replace(/Location:\s*/i, "").trim().split("\n")[0];
  } else {
    const metaDivs = Array.from(document.querySelectorAll(".meta-item, div, span"));
    const found = metaDivs.find(d => d.innerText && d.innerText.includes("Location:"));
    if (found) result.location = found.innerText.replace(/Location:\s*/i, "").trim();
  }

  // 3c. Job Type
  const typeEl = document.querySelector("#job-type, [class*='employment-type'], [class*='job-type']");
  if (typeEl) {
    result.job_type = typeEl.innerText.replace(/Employment Type:\s*/i, "").trim().split("\n")[0];
  } else {
    const metaDivs = Array.from(document.querySelectorAll(".meta-item, div, span"));
    const found = metaDivs.find(d => d.innerText && d.innerText.includes("Employment Type:"));
    if (found) result.job_type = found.innerText.replace(/Employment Type:\s*/i, "").trim();
  }

  // 4. Extract Description
  const descSelectors = [
    "#job-description",
    ".job-description",
    "#description",
    "[data-automation-id='jobDescription']",
    ".show-more-less-html__markup",
    "#jobDescriptionText",
    "article",
    ".description"
  ];
  for (const sel of descSelectors) {
    const el = document.querySelector(sel);
    if (el && el.innerText.trim().length > 20) {
      result.description = el.innerText.trim();
      break;
    }
  }

  // 5. Extract Requirements / Qualifications
  const reqSelectors = [
    "#job-requirements",
    ".job-requirements",
    "#requirements",
    "#qualifications",
    "[class*='requirement']",
    "[class*='qualification']"
  ];
  for (const sel of reqSelectors) {
    const el = document.querySelector(sel);
    if (el && el.innerText.trim().length > 10) {
      result.requirements = el.innerText.trim();
      break;
    }
  }

  // 6. Extract Recruiter / Contact Email
  const explicitEmailEl = document.querySelector("#recruiter-email, a[href^='mailto:']");
  if (explicitEmailEl) {
    const text = explicitEmailEl.innerText || explicitEmailEl.getAttribute("href") || "";
    const match = text.match(/[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+/);
    if (match) {
      result.recruiter_email = match[0];
    }
  }

  if (!result.recruiter_email) {
    const bodyText = document.body ? document.body.innerText : "";
    const emailMatches = bodyText.match(/[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+/g);
    if (emailMatches && emailMatches.length > 0) {
      for (const em of emailMatches) {
        if (!em.endsWith(".png") && !em.endsWith(".jpg") && !em.endsWith(".svg")) {
          result.recruiter_email = em;
          break;
        }
      }
    }
  }

  // 7. Extract Application Link
  const appLinkEl = document.querySelector("#application-link, a[class*='apply'], a.btn-apply, a[href*='apply']");
  if (appLinkEl && appLinkEl.href) {
    result.application_link = appLinkEl.href;
  }

  // 8. General fallback if specific containers were not identified
  if (!result.description || result.description.length < 50) {
    const paragraphs = Array.from(document.querySelectorAll("p, li"))
      .map(p => p.innerText.trim())
      .filter(t => t.length > 25);
    if (paragraphs.length > 0) {
      result.description = (result.description ? result.description + "\n\n" : "") + paragraphs.slice(0, 15).join("\n");
    }
  }

  return result;
}

// Listen for message from popup
if (typeof chrome !== "undefined" && chrome.runtime && chrome.runtime.onMessage) {
  chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
    if (request.action === "extract_job") {
      try {
        const jobData = extractJobInformation();
        sendResponse({ success: true, data: jobData });
      } catch (err) {
        sendResponse({ success: false, error: err.message });
      }
    }
    return true;
  });
}

// -------------------------------------------------------------
// Auto In-Page Popup Assistant Widget
// Automatically displays when viewing a Job Description page
// -------------------------------------------------------------
(function initInPageAssistant() {
  // Only inject if not already injected and page has substantive content
  if (document.getElementById("jobshield-widget-container")) return;

  // Give DOM 400ms to settle
  setTimeout(() => {
    const jobData = extractJobInformation();
    const wordCount = (jobData.title + " " + jobData.description + " " + jobData.requirements).split(/\s+/).length;

    // Check if on a job page (either title is detected or url is a demo job)
    const isJobPage = Boolean(
      jobData.title ||
      document.querySelector("#job-description, #job-requirements, .job-description") ||
      window.location.pathname.includes(".html") && !window.location.pathname.endsWith("index.html")
    );

    if (isJobPage && wordCount >= 8) {
      renderAssistantWidget(jobData);
    }
  }, 400);
})();

function renderAssistantWidget(jobData) {
  const container = document.createElement("div");
  container.id = "jobshield-widget-container";
  container.style.cssText = `
    position: fixed;
    bottom: 24px;
    right: 24px;
    z-index: 999999;
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
    color: #0f172a;
    box-sizing: border-box;
  `;

  // Inject Styles for Widget
  const styleEl = document.createElement("style");
  styleEl.textContent = `
    #jobshield-widget-container * { box-sizing: border-box; margin: 0; padding: 0; }
    .js-launcher-btn {
      display: flex;
      align-items: center;
      gap: 8px;
      background: #0284c7;
      color: #ffffff;
      border: 1px solid #0369a1;
      padding: 10px 18px;
      border-radius: 999px;
      font-size: 13px;
      font-weight: 600;
      cursor: pointer;
      box-shadow: 0 4px 14px rgba(2, 132, 199, 0.35);
      transition: all 0.2s ease;
    }
    .js-launcher-btn:hover {
      background: #0369a1;
      transform: translateY(-2px);
      box-shadow: 0 6px 20px rgba(2, 132, 199, 0.45);
    }
    .js-popup-card {
      width: 370px;
      max-height: 520px;
      overflow-y: auto;
      background: #ffffff;
      border: 1px solid #bae6fd;
      border-radius: 14px;
      box-shadow: 0 10px 30px rgba(2, 132, 199, 0.15), 0 4px 12px rgba(0, 0, 0, 0.08);
      padding: 18px;
      margin-bottom: 12px;
      animation: jsSlideUp 0.25s cubic-bezier(0.16, 1, 0.3, 1);
    }
    @keyframes jsSlideUp {
      from { opacity: 0; transform: translateY(16px); }
      to { opacity: 1; transform: translateY(0); }
    }
    .js-header {
      display: flex;
      justify-content: space-between;
      align-items: center;
      padding-bottom: 12px;
      border-bottom: 1px solid #e2e8f0;
      margin-bottom: 12px;
    }
    .js-brand {
      display: flex;
      align-items: center;
      gap: 8px;
      font-weight: 700;
      font-size: 14px;
      color: #0f172a;
    }
    .js-brand span { color: #0284c7; }
    .js-close-btn {
      background: #f1f5f9;
      border: none;
      width: 26px;
      height: 26px;
      border-radius: 6px;
      cursor: pointer;
      font-weight: 700;
      color: #64748b;
      display: flex;
      align-items: center;
      justify-content: center;
      font-size: 14px;
    }
    .js-close-btn:hover { background: #e2e8f0; color: #0f172a; }
    .js-risk-row {
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-bottom: 10px;
    }
    .js-pill {
      font-size: 11px;
      font-weight: 700;
      padding: 3px 8px;
      border-radius: 6px;
      text-transform: uppercase;
    }
    .js-pill.low { background: #ecfdf5; color: #059669; border: 1px solid #a7f3d0; }
    .js-pill.medium { background: #fffbeb; color: #d97706; border: 1px solid #fde68a; }
    .js-pill.high { background: #fef2f2; color: #dc2626; border: 1px solid #fecaca; }
    .js-pill.insufficient { background: #f1f5f9; color: #475569; border: 1px solid #cbd5e1; }
    .js-score-num { font-size: 15px; font-weight: 800; color: #0f172a; }
    .js-progress {
      width: 100%;
      height: 6px;
      background: #f1f5f9;
      border-radius: 999px;
      overflow: hidden;
      margin-bottom: 12px;
    }
    .js-progress-fill { height: 100%; border-radius: 999px; }
    .js-progress-fill.low { background: #059669; }
    .js-progress-fill.medium { background: #d97706; }
    .js-progress-fill.high { background: #dc2626; }
    .js-progress-fill.insufficient { background: #64748b; }
    .js-scores-grid {
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 8px;
      background: #f0f7ff;
      border: 1px solid #bae6fd;
      padding: 8px 10px;
      border-radius: 6px;
      margin-bottom: 12px;
      font-size: 11.5px;
    }
    .js-llm-card {
      background: #ffffff;
      border: 1px solid #bae6fd;
      border-radius: 8px;
      padding: 10px 12px;
      margin-bottom: 12px;
    }
    .js-llm-title {
      font-size: 11px;
      font-weight: 700;
      color: #0284c7;
      margin-bottom: 4px;
      display: flex;
      justify-content: space-between;
    }
    .js-llm-text {
      font-size: 11.5px;
      color: #1e293b;
      line-height: 1.5;
    }
    .js-llm-text strong {
      color: #0f172a;
      font-weight: 700;
    }
    .js-llm-text .bullet-item {
      display: flex;
      gap: 6px;
      align-items: baseline;
      margin-top: 3px;
    }
    .js-llm-text .bullet-dot {
      color: #0284c7;
      font-weight: 800;
      font-size: 12px;
      line-height: 1;
    }
    .js-llm-text .paragraph-break {
      height: 6px;
    }
    .js-warning-item {
      background: #fef2f2;
      border-left: 3px solid #dc2626;
      border-radius: 6px;
      padding: 8px 10px;
      margin-bottom: 6px;
      font-size: 11.5px;
    }
    .js-warning-item strong { color: #991b1b; }
    .js-disclaimer {
      font-size: 10px;
      color: #94a3b8;
      text-align: center;
      margin-top: 10px;
      border-top: 1px solid #f1f5f9;
      padding-top: 8px;
    }
  `;
  document.head.appendChild(styleEl);

  // Initial loading button
  const launcher = document.createElement("button");
  launcher.className = "js-launcher-btn";
  launcher.innerHTML = `<span>🛡️</span><span>JobShield: Assessing Risk...</span>`;
  container.appendChild(launcher);
  document.body.appendChild(container);

  // Automatically query backend
  fetch(`${BACKEND_URL}/analyze`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(jobData)
  })
  .then(res => res.json())
  .then(data => {
    const riskLevel = (data.risk_level || "UNKNOWN").toUpperCase();
    const riskClass = riskLevel.toLowerCase().includes("low") ? "low" :
                     riskLevel.toLowerCase().includes("med") ? "medium" :
                     riskLevel.toLowerCase().includes("high") ? "high" : "insufficient";

    // Update Launcher Text
    launcher.innerHTML = `<span>🛡️</span><span>JobShield: ${riskLevel} (${data.risk_score}/100)</span>`;
    if (riskClass === "high") {
      launcher.style.background = "#dc2626";
      launcher.style.borderColor = "#b91c1c";
      launcher.style.boxShadow = "0 4px 14px rgba(220, 38, 38, 0.35)";
    } else if (riskClass === "low") {
      launcher.style.background = "#059669";
      launcher.style.borderColor = "#047857";
      launcher.style.boxShadow = "0 4px 14px rgba(5, 150, 105, 0.35)";
    }

    // Create Popup Card
    const card = document.createElement("div");
    card.className = "js-popup-card";
    
    // Warnings HTML
    let warningsHtml = "";
    if (data.detailed_warnings && data.detailed_warnings.length > 0) {
      warningsHtml = `<div style="margin-bottom: 10px;"><strong style="font-size: 11.5px; color: #dc2626;">⚠️ Warning Indicators (${data.detailed_warnings.length}):</strong></div>`;
      data.detailed_warnings.slice(0, 3).forEach(w => {
        warningsHtml += `
          <div class="js-warning-item">
            <strong>${w.name} (${w.severity})</strong>
            <p style="color: #475569; margin-top: 2px;">${w.explanation}</p>
          </div>
        `;
      });
    }

    // LLM Explainer HTML
    let llmHtml = "";
    if (data.llm_explanation) {
      llmHtml = `
        <div class="js-llm-card">
          <div class="js-llm-title">
            <span>✨ AI Threat Intelligence</span>
            <span style="font-weight: 500; font-size: 9.5px; color: #64748b;">${data.llm_source || "AI Threat Intelligence"}</span>
          </div>
          <div class="js-llm-text">${formatWidgetMarkdown(data.llm_explanation)}</div>
        </div>
      `;
    }

    card.innerHTML = `
      <div class="js-header">
        <div class="js-brand">
          <span style="font-size: 16px;">🛡️</span>
          <div>JobShield <span>AI</span></div>
        </div>
        <button class="js-close-btn" id="js-minimize-btn" title="Minimize">✕</button>
      </div>

      <div class="js-risk-row">
        <span class="js-pill ${riskClass}">${riskLevel.replace("_", " ")} RISK</span>
        <span class="js-score-num">${data.risk_score}<span style="font-size: 11px; font-weight: 500; color: #64748b;">/100</span></span>
      </div>

      <div class="js-progress">
        <div class="js-progress-fill ${riskClass}" style="width: ${Math.min(100, Math.max(0, data.risk_score))}%;"></div>
      </div>

      <div class="js-scores-grid">
        <div><span style="color: #64748b;">ML Probability:</span> <strong>${data.ml_score !== null ? data.ml_score + '%' : 'N/A'}</strong></div>
        <div><span style="color: #64748b;">Rule Score:</span> <strong>${data.rule_score}/100</strong></div>
      </div>

      ${llmHtml}
      ${warningsHtml}

      <div class="js-disclaimer">
        This assessment is decision-support only and is not proof of fraud or legitimacy.
      </div>
    `;

    // Automatically show popup card on page load
    container.insertBefore(card, launcher);

    // Minimize button toggle
    card.querySelector("#js-minimize-btn").addEventListener("click", () => {
      card.style.display = "none";
    });

    launcher.addEventListener("click", () => {
      card.style.display = card.style.display === "none" ? "block" : "none";
    });
  })
  .catch(err => {
    launcher.innerHTML = `<span>🛡️</span><span>JobShield: Ready</span>`;
    launcher.title = "Could not connect to FastAPI server (http://127.0.0.1:8000)";
  });
}

function formatWidgetMarkdown(text) {
  if (!text) return "";
  const div = document.createElement("div");
  div.textContent = text;
  let safe = div.innerHTML;

  safe = safe.replace(/\*\*(.*?)\*\*/g, "<strong>$1</strong>");
  safe = safe.replace(/^[•\-\*]\s+(.*)$/gm, "<div class='bullet-item'><span class='bullet-dot'>•</span><span>$1</span></div>");
  safe = safe.replace(/\n\n+/g, "<div class='paragraph-break'></div>");
  safe = safe.replace(/\n/g, "<br>");
  return safe;
}
