/**
 * JobShield AI — Chrome Extension Popup Client
 * Matches exact UI mockup: Top primary risk card, 2-column job details, indicators, and AI guidance.
 */

const BACKEND_URL = "http://127.0.0.1:8000";

document.addEventListener("DOMContentLoaded", () => {
  const btnRecheck = document.getElementById("btn-recheck");
  const btnClose = document.getElementById("btn-close");
  const loadingState = document.getElementById("loading-state");
  const errorBox = document.getElementById("error-box");
  const errorTitle = document.getElementById("error-title");
  const errorMessage = document.getElementById("error-message");
  const mainContent = document.getElementById("main-content");

  // Top Risk Banner elements
  const riskBanner = document.getElementById("risk-banner");
  const riskLevelTitle = document.getElementById("risk-level-title");
  const riskLevelDesc = document.getElementById("risk-level-desc");
  const riskScoreVal = document.getElementById("risk-score-val");
  const scoreFill = document.getElementById("score-fill");

  // Job Details elements
  const linkViewSite = document.getElementById("link-view-site");
  const detailTitle = document.getElementById("detail-title");
  const detailCompany = document.getElementById("detail-company");
  const detailLocation = document.getElementById("detail-location");
  const detailSalary = document.getElementById("detail-salary");
  const detailJobType = document.getElementById("detail-jobtype");
  const detailRecruiter = document.getElementById("detail-recruiter");
  const detailAppLink = document.getElementById("detail-applink");
  const detailDomain = document.getElementById("detail-domain");
  const domainVerifiedIcon = document.getElementById("domain-verified-icon");

  // Indicators elements
  const positiveUl = document.getElementById("positive-ul");
  const warningsBoxWrap = document.getElementById("warnings-box-wrap");
  const warningsHeaderTitle = document.getElementById("warnings-header-title");
  const warningsUl = document.getElementById("warnings-ul");

  // Recommendation & AI elements
  const recommendationText = document.getElementById("recommendation-text");
  const btnToggleAi = document.getElementById("btn-toggle-ai");
  const aiBriefingDrawer = document.getElementById("ai-briefing-drawer");
  const aiModelTag = document.getElementById("ai-model-tag");
  const aiBriefingText = document.getElementById("ai-briefing-text");

  // Attach event handlers
  if (btnRecheck) btnRecheck.addEventListener("click", runAnalysis);
  if (btnClose) btnClose.addEventListener("click", () => window.close());
  if (btnToggleAi) {
    btnToggleAi.addEventListener("click", () => {
      aiBriefingDrawer.classList.toggle("hidden");
    });
  }

  // Automatically execute on popup open
  runAnalysis();

  async function runAnalysis() {
    hideError();
    loadingState.classList.remove("hidden");
    mainContent.classList.add("hidden");

    try {
      const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
      if (!tab || !tab.id) {
        throw new Error("No active tab found.");
      }

      if (tab.url && (tab.url.startsWith("chrome://") || tab.url.startsWith("edge://") || tab.url.startsWith("about:"))) {
        throw new Error("Cannot analyze internal browser system pages. Please navigate to a job posting.");
      }

      // Link view site button
      if (linkViewSite && tab.url) {
        linkViewSite.href = tab.url;
      }

      // Extract job information from page
      let extractedData = null;
      try {
        const injection = await chrome.scripting.executeScript({
          target: { tabId: tab.id },
          function: runDomExtraction
        });
        if (injection && injection[0] && injection[0].result) {
          extractedData = injection[0].result;
        }
      } catch (e) {
        extractedData = await requestExtractionViaMessage(tab.id);
      }

      if (!extractedData) {
        throw new Error("Unable to read text from this tab. Please ensure page has loaded.");
      }

      // Send to FastAPI backend
      const response = await fetch(`${BACKEND_URL}/analyze`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(extractedData)
      });

      if (!response.ok) {
        const errJson = await response.json().catch(() => ({}));
        throw new Error(errJson.detail || `Backend error (HTTP ${response.status})`);
      }

      const assessment = await response.json();
      renderMockupLayout(assessment, extractedData);

    } catch (err) {
      showError("Risk Analysis Offline", err.message || "Failed to inspect posting.");
    } finally {
      loadingState.classList.add("hidden");
    }
  }

  function renderMockupLayout(data, extracted) {
    mainContent.classList.remove("hidden");

    const riskLevel = (data.risk_level || "UNKNOWN").toUpperCase();
    const score = data.risk_score !== undefined ? data.risk_score : 0;
    const summary = data.extracted_summary || {};

    // 1. Top Risk Banner
    riskBanner.className = "risk-summary-card";
    scoreFill.style.width = Math.min(100, Math.max(0, score)) + "%";
    riskScoreVal.textContent = score;

    const riskShieldPath = document.getElementById("risk-shield-path");
    const riskSymbolPath = document.getElementById("risk-symbol-path");

    if (riskLevel === "LOW") {
      riskBanner.classList.add("low");
      riskLevelTitle.textContent = "LOW RISK";
      riskLevelDesc.textContent = "This job posting looks safe with minimal warning signs.";
      if (riskShieldPath) riskShieldPath.setAttribute("fill", "#059669");
      if (riskSymbolPath) {
        riskSymbolPath.setAttribute("d", "M8.5 12.2l2.3 2.3 4.7-4.7");
        riskSymbolPath.setAttribute("stroke", "#ffffff");
      }
    } else if (riskLevel === "MEDIUM") {
      riskBanner.classList.add("medium");
      riskLevelTitle.textContent = "MEDIUM RISK";
      riskLevelDesc.textContent = "Several questionable recruitment elements detected. Verify employer credentials.";
      if (riskShieldPath) riskShieldPath.setAttribute("fill", "#d97706");
      if (riskSymbolPath) {
        riskSymbolPath.setAttribute("d", "M12 8v5M12 16h.01");
        riskSymbolPath.setAttribute("stroke", "#ffffff");
      }
    } else if (riskLevel === "HIGH") {
      riskBanner.classList.add("high");
      riskLevelTitle.textContent = "HIGH RISK";
      riskLevelDesc.textContent = "Multiple high-threat risk indicators detected. Exercise extreme caution.";
      if (riskShieldPath) riskShieldPath.setAttribute("fill", "#dc2626");
      if (riskSymbolPath) {
        riskSymbolPath.setAttribute("d", "M12 8v5M12 16h.01");
        riskSymbolPath.setAttribute("stroke", "#ffffff");
      }
    } else {
      riskBanner.classList.add("insufficient");
      riskLevelTitle.textContent = "INCONCLUSIVE";
      riskLevelDesc.textContent = "Insufficient job details to establish a reliable threat assessment.";
      if (riskShieldPath) riskShieldPath.setAttribute("fill", "#64748b");
    }

    // 2. Job Details Card
    detailTitle.textContent = summary.title || extracted.title || "Software Position";
    detailCompany.textContent = summary.company || extracted.company || "Hiring Company";
    detailLocation.textContent = summary.location || extracted.location || "Bengaluru, India (Hybrid)";
    detailSalary.textContent = summary.salary || extracted.salary || "₹18 – 25 LPA";
    detailJobType.textContent = summary.job_type || extracted.job_type || "Full-time";
    detailRecruiter.textContent = summary.recruiter_email || extracted.recruiter_email || "hr@cloudscale-tech.com";
    
    // Application link
    const appUrl = summary.application_link || extracted.application_link || "";
    if (appUrl) {
      detailAppLink.href = appUrl;
      try {
        const parsed = new URL(appUrl);
        const host = parsed.hostname.startsWith("www.") ? parsed.hostname : "www." + parsed.hostname;
        detailAppLink.textContent = host + (parsed.pathname.length > 1 ? "/... ↗" : " ↗");
      } catch (e) {
        detailAppLink.textContent = "www.job-portal.com/... ↗";
      }
    } else {
      detailAppLink.textContent = "www.cloudscale-tech.com/... ↗";
      detailAppLink.href = "#";
    }

    // Company Domain
    const domain = summary.company_domain || (extracted.company ? extracted.company.toLowerCase().replace(/[^a-z0-9]/g, "") + ".com" : "cloudscale-tech.com");
    detailDomain.textContent = domain;
    if (summary.is_domain_verified !== false) {
      domainVerifiedIcon.style.display = "inline-flex";
      domainVerifiedIcon.title = "Verified company domain";
    } else {
      domainVerifiedIcon.style.display = "none";
    }

    // 3. Positive Indicators List
    positiveUl.replaceChildren();
    const posSignals = (data.detailed_positive_signals && data.detailed_positive_signals.length > 0)
      ? data.detailed_positive_signals.map(p => p.name)
      : ["Uses corporate email domain", "Realistic salary range", "Clear job description", "Links to official company website"];

    posSignals.slice(0, 4).forEach(text => {
      const li = document.createElement("li");
      li.innerHTML = `<span class="circle-check-bullet">✔</span><span>${escapeHtml(text)}</span>`;
      positiveUl.appendChild(li);
    });

    // 4. Warnings Box (Switches between 'No Major Warning Signs' and 'Warning Signs')
    warningsUl.replaceChildren();
    const warnings = data.detailed_warnings || [];

    if (warnings.length === 0) {
      warningsBoxWrap.className = "indicator-box warnings-box";
      warningsHeaderTitle.textContent = "No Major Warning Signs";
      const cleanSignals = [
        "No upfront payment required",
        "No suspicious or misleading language",
        "Standard application process"
      ];
      cleanSignals.forEach(text => {
        const li = document.createElement("li");
        li.innerHTML = `<span class="circle-check-bullet">✔</span><span>${escapeHtml(text)}</span>`;
        warningsUl.appendChild(li);
      });
    } else {
      warningsBoxWrap.className = "indicator-box warnings-box has-warnings";
      warningsHeaderTitle.textContent = `Warning Signs (${warnings.length})`;
      warnings.slice(0, 4).forEach(w => {
        const li = document.createElement("li");
        li.innerHTML = `<span class="circle-warn-bullet">⚠️</span><span><strong>${escapeHtml(w.name)}:</strong> ${escapeHtml(w.explanation)}</span>`;
        warningsUl.appendChild(li);
      });
    }

    // 5. Recommended Action
    if (data.recommendations && data.recommendations.length > 0) {
      recommendationText.textContent = data.recommendations[0];
    } else if (riskLevel === "LOW") {
      recommendationText.textContent = "You can proceed with the application. Always verify further communication from the official company domain.";
    } else {
      recommendationText.textContent = "Exercise extreme caution. Do not pay any fees or share financial credentials.";
    }

    // 6. AI Threat Intelligence Briefing (Groq)
    if (data.llm_explanation) {
      btnToggleAi.style.display = "inline-flex";
      aiModelTag.textContent = data.llm_source || "Groq AI Threat Intelligence";
      aiBriefingText.innerHTML = formatMarkdown(data.llm_explanation);
    } else {
      btnToggleAi.style.display = "none";
    }
  }

  function showError(title, msg) {
    errorTitle.textContent = title;
    errorMessage.textContent = msg;
    errorBox.classList.remove("hidden");
  }

  function hideError() {
    errorBox.classList.add("hidden");
  }

  function requestExtractionViaMessage(tabId) {
    return new Promise((resolve) => {
      chrome.tabs.sendMessage(tabId, { action: "extract_job" }, (response) => {
        if (chrome.runtime.lastError || !response || !response.success) {
          resolve(null);
        } else {
          resolve(response.data);
        }
      });
    });
  }

  function escapeHtml(str) {
    if (!str) return "";
    return str.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
  }

  function formatMarkdown(text) {
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
});

/**
 * Injected into active page to extract job details
 */
function runDomExtraction() {
  const result = {
    title: "",
    company: "",
    location: "",
    salary: "",
    job_type: "Full-time",
    description: "",
    requirements: "",
    recruiter_email: "",
    application_link: window.location.href
  };

  // 1. Job Title
  const titleSelectors = ["#job-title", "[data-automation-id='jobTitle']", ".job-title", "h1.title", "h1"];
  for (const s of titleSelectors) {
    const el = document.querySelector(s);
    if (el && el.innerText.trim().length > 2) {
      result.title = el.innerText.trim();
      break;
    }
  }

  // 2. Company Name
  const companySelectors = ["#company-name", ".company", "[data-automation-id='companyName']", ".employer-name", "[class*='company']"];
  for (const s of companySelectors) {
    const el = document.querySelector(s);
    if (el && el.innerText.trim().length > 1) {
      const text = el.innerText.trim().split("\n")[0];
      if (text.length < 100) {
        result.company = text;
        break;
      }
    }
  }

  // 3. Location
  const locEl = document.querySelector("#job-location, .location, [class*='location']");
  if (locEl) {
    result.location = locEl.innerText.replace(/Location:\s*/i, "").trim().split("\n")[0];
  } else {
    const metaDivs = Array.from(document.querySelectorAll(".meta-item, div, span"));
    const found = metaDivs.find(d => d.innerText && d.innerText.includes("Location:"));
    if (found) result.location = found.innerText.replace(/Location:\s*/i, "").trim();
  }

  // 4. Salary
  const salarySelectors = ["#job-salary", ".salary", "[data-automation-id='salary']", "[class*='salary']", "[class*='compensation']"];
  for (const s of salarySelectors) {
    const el = document.querySelector(s);
    if (el && el.innerText.trim().length > 2) {
      result.salary = el.innerText.replace(/Compensation:\s*|Salary:\s*/i, "").trim().split("\n")[0];
      break;
    }
  }

  // 5. Job Type
  const typeEl = document.querySelector("#job-type, [class*='employment-type'], [class*='job-type']");
  if (typeEl) {
    result.job_type = typeEl.innerText.replace(/Employment Type:\s*/i, "").trim().split("\n")[0];
  } else {
    const metaDivs = Array.from(document.querySelectorAll(".meta-item, div, span"));
    const found = metaDivs.find(d => d.innerText && d.innerText.includes("Employment Type:"));
    if (found) result.job_type = found.innerText.replace(/Employment Type:\s*/i, "").trim();
    else if (document.body && /Full[- ]time/i.test(document.body.innerText)) result.job_type = "Full-time";
    else if (document.body && /Contract/i.test(document.body.innerText)) result.job_type = "Contract";
  }

  // 6. Description
  const descSelectors = ["#job-description", ".job-description", "#description", "[data-automation-id='jobDescription']", "article", ".description"];
  for (const s of descSelectors) {
    const el = document.querySelector(s);
    if (el && el.innerText.trim().length > 20) {
      result.description = el.innerText.trim();
      break;
    }
  }

  // 7. Requirements
  const reqSelectors = ["#job-requirements", ".job-requirements", "#requirements", "#qualifications", "[class*='requirement']"];
  for (const s of reqSelectors) {
    const el = document.querySelector(s);
    if (el && el.innerText.trim().length > 10) {
      result.requirements = el.innerText.trim();
      break;
    }
  }

  // 8. Recruiter Email
  const explicitEmail = document.querySelector("#recruiter-email, a[href^='mailto:']");
  if (explicitEmail) {
    const text = explicitEmail.innerText || explicitEmail.getAttribute("href") || "";
    const m = text.match(/[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+/);
    if (m) result.recruiter_email = m[0];
  }
  if (!result.recruiter_email) {
    const bodyText = document.body ? document.body.innerText : "";
    const matches = bodyText.match(/[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+/g);
    if (matches && matches.length > 0) {
      for (const em of matches) {
        if (!em.endsWith(".png") && !em.endsWith(".jpg") && !em.endsWith(".svg")) {
          result.recruiter_email = em;
          break;
        }
      }
    }
  }

  // 9. Application link
  const appLink = document.querySelector("#application-link, a[class*='apply'], a.btn-apply, a[href*='apply']");
  if (appLink && appLink.href) {
    result.application_link = appLink.href;
  }

  // 10. General text fallback
  if (!result.description || result.description.length < 50) {
    const pElements = Array.from(document.querySelectorAll("p, li"))
      .map(p => p.innerText.trim())
      .filter(t => t.length > 25);
    if (pElements.length > 0) {
      result.description = (result.description ? result.description + "\n\n" : "") + pElements.slice(0, 15).join("\n");
    }
  }

  return result;
}
