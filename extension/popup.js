/**
 * JobShield AI — Chrome Extension Popup Logic
 * Communicates with content script on active tab and FastAPI backend at http://127.0.0.1:8000
 */

const BACKEND_URL = "http://127.0.0.1:8000";

document.addEventListener("DOMContentLoaded", () => {
  const btnCheckRisk = document.getElementById("btn-check-risk");
  const backendIndicator = document.getElementById("backend-status-indicator");
  const backendStatusText = document.getElementById("backend-status-text");
  const detectionStatus = document.getElementById("detection-status");
  const previewTitle = document.getElementById("preview-title");
  const previewCompany = document.getElementById("preview-company");
  const loadingState = document.getElementById("loading-state");
  const errorBox = document.getElementById("error-box");
  const errorTitle = document.getElementById("error-title");
  const errorMessage = document.getElementById("error-message");
  const resultsContainer = document.getElementById("results-container");

  // Score elements
  const riskPill = document.getElementById("risk-pill");
  const finalScoreVal = document.getElementById("final-score-val");
  const scoreFillBar = document.getElementById("score-fill-bar");
  const mlScoreVal = document.getElementById("ml-score-val");
  const ruleScoreVal = document.getElementById("rule-score-val");
  const explanationText = document.getElementById("explanation-text");

  // Indicators elements
  const warningsSection = document.getElementById("warnings-section");
  const warningsList = document.getElementById("warnings-list");
  const warningsCount = document.getElementById("warnings-count");
  const positiveSection = document.getElementById("positive-section");
  const positiveList = document.getElementById("positive-list");
  const positiveCount = document.getElementById("positive-count");
  const recsSection = document.getElementById("recs-section");
  const recsList = document.getElementById("recs-list");
  const disclaimerText = document.getElementById("disclaimer-text");

  // Check backend health on startup
  checkBackendHealth();

  // Attach button click event
  btnCheckRisk.addEventListener("click", () => {
    executeJobRiskAnalysis();
  });

  async function checkBackendHealth() {
    try {
      const resp = await fetch(`${BACKEND_URL}/health`, { method: "GET" });
      if (resp.ok) {
        const data = await resp.json();
        backendIndicator.className = "backend-badge connected";
        backendStatusText.textContent = data.model_loaded ? "Backend Online" : "Degraded (No ML)";
      } else {
        throw new Error("HTTP " + resp.status);
      }
    } catch (e) {
      backendIndicator.className = "backend-badge error";
      backendStatusText.textContent = "Backend Offline";
    }
  }

  async function executeJobRiskAnalysis() {
    // Reset state
    hideError();
    resultsContainer.classList.add("hidden");
    loadingState.classList.remove("hidden");
    btnCheckRisk.disabled = true;

    try {
      // Step 1: Query Active Tab
      const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
      if (!tab || !tab.id) {
        throw new Error("No active browser tab found to inspect.");
      }

      // Check for restricted URLs (chrome:// or edge://)
      if (tab.url.startsWith("chrome://") || tab.url.startsWith("edge://") || tab.url.startsWith("about:")) {
        throw new Error("Cannot run risk analysis on internal browser system pages. Please navigate to a job posting webpage.");
      }

      // Step 2: Extract job data from page via script injection
      let extractedData = null;
      try {
        const injectionResults = await chrome.scripting.executeScript({
          target: { tabId: tab.id },
          function: runDomExtraction
        });

        if (injectionResults && injectionResults[0] && injectionResults[0].result) {
          extractedData = injectionResults[0].result;
        }
      } catch (injectionErr) {
        // Fallback message passing if scripting fails
        extractedData = await requestExtractionViaMessage(tab.id);
      }

      if (!extractedData) {
        throw new Error("Unable to extract text from this webpage. Please ensure page has completed loading.");
      }

      // Update UI preview
      previewTitle.textContent = extractedData.title || "(No explicit title found)";
      previewCompany.textContent = extractedData.company || "(Not specified)";
      detectionStatus.textContent = "Extracted";
      detectionStatus.style.color = "#38bdf8";

      // Step 3: Send POST to FastAPI backend
      const response = await fetch(`${BACKEND_URL}/analyze`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(extractedData)
      });

      if (!response.ok) {
        const errJson = await response.json().catch(() => ({}));
        throw new Error(errJson.detail || `Server returned error status ${response.status}`);
      }

      const assessment = await response.json();

      // Step 4: Render Assessment
      renderAssessmentResults(assessment);

    } catch (err) {
      showError("Analysis Failed", err.message || "An unexpected error occurred.");
    } finally {
      loadingState.classList.add("hidden");
      btnCheckRisk.disabled = false;
    }
  }

  function renderAssessmentResults(data) {
    // Risk Level & Color Schemes
    const level = (data.risk_level || "UNKNOWN").toUpperCase();
    riskPill.textContent = level.replace("_", " ") + (level !== "INSUFFICIENT_INFO" ? " RISK" : "");
    riskPill.className = "risk-pill";

    scoreFillBar.className = "score-fill";

    if (level === "LOW") {
      riskPill.classList.add("low");
      scoreFillBar.classList.add("low");
    } else if (level === "MEDIUM") {
      riskPill.classList.add("medium");
      scoreFillBar.classList.add("medium");
    } else if (level === "HIGH") {
      riskPill.classList.add("high");
      scoreFillBar.classList.add("high");
    } else {
      riskPill.classList.add("insufficient");
      scoreFillBar.classList.add("insufficient");
    }

    // Score numbers
    const score = data.risk_score !== undefined ? data.risk_score : 0;
    finalScoreVal.textContent = score;
    scoreFillBar.style.width = Math.min(100, Math.max(0, score)) + "%";

    mlScoreVal.textContent = data.ml_score !== null && data.ml_score !== undefined ? data.ml_score + "%" : "N/A";
    ruleScoreVal.textContent = data.rule_score !== undefined ? data.rule_score + "/100" : "N/A";

    // Explanation
    explanationText.textContent = data.explanation || "No explanation provided.";

    // Render Warnings (Safe DOM)
    warningsList.replaceChildren();
    const detailedWarnings = data.detailed_warnings || [];
    warningsCount.textContent = detailedWarnings.length;

    if (detailedWarnings.length > 0) {
      warningsSection.classList.remove("hidden");
      detailedWarnings.forEach(w => {
        const item = document.createElement("div");
        item.className = `indicator-item ${(w.severity || "low").toLowerCase()}`;

        const header = document.createElement("div");
        header.className = "indicator-header";

        const nameSpan = document.createElement("span");
        nameSpan.className = "indicator-name";
        nameSpan.textContent = w.name || "Risk Indicator";

        const tag = document.createElement("span");
        tag.className = `severity-tag ${(w.severity || "low").toLowerCase()}`;
        tag.textContent = w.severity || "Low";

        header.appendChild(nameSpan);
        header.appendChild(tag);
        item.appendChild(header);

        const desc = document.createElement("div");
        desc.className = "indicator-desc";
        desc.textContent = w.explanation || "";
        item.appendChild(desc);

        if (w.evidence) {
          const evidence = document.createElement("div");
          evidence.className = "indicator-evidence";
          evidence.textContent = `Evidence: ${w.evidence}`;
          item.appendChild(evidence);
        }

        warningsList.appendChild(item);
      });
    } else {
      warningsSection.classList.add("hidden");
    }

    // Render Positive Signals (Safe DOM)
    positiveList.replaceChildren();
    const detailedPositive = data.detailed_positive_signals || [];
    positiveCount.textContent = detailedPositive.length;

    if (detailedPositive.length > 0) {
      positiveSection.classList.remove("hidden");
      detailedPositive.forEach(p => {
        const item = document.createElement("div");
        item.className = "indicator-item positive";

        const header = document.createElement("div");
        header.className = "indicator-header";

        const nameSpan = document.createElement("span");
        nameSpan.className = "indicator-name";
        nameSpan.textContent = p.name || "Consistency Signal";

        header.appendChild(nameSpan);
        item.appendChild(header);

        const desc = document.createElement("div");
        desc.className = "indicator-desc";
        desc.textContent = p.explanation || "";
        item.appendChild(desc);

        if (p.evidence) {
          const evidence = document.createElement("div");
          evidence.className = "indicator-evidence";
          evidence.textContent = `Observed: ${p.evidence}`;
          item.appendChild(evidence);
        }

        positiveList.appendChild(item);
      });
    } else {
      positiveSection.classList.add("hidden");
    }

    // Render Recommendations
    recsList.replaceChildren();
    const recs = data.recommendations || [];
    if (recs.length > 0) {
      recsSection.classList.remove("hidden");
      recs.forEach(r => {
        const li = document.createElement("li");
        li.textContent = r;
        recsList.appendChild(li);
      });
    } else {
      recsSection.classList.add("hidden");
    }

    // Disclaimer
    if (data.disclaimer) {
      disclaimerText.textContent = data.disclaimer;
    }

    resultsContainer.classList.remove("hidden");
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
});

/**
 * Injected into active page to extract job details
 */
function runDomExtraction() {
  const result = {
    title: "",
    company: "",
    description: "",
    requirements: "",
    salary: "",
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

  // 3. Salary
  const salarySelectors = ["#job-salary", ".salary", "[data-automation-id='salary']", "[class*='salary']", "[class*='compensation']"];
  for (const s of salarySelectors) {
    const el = document.querySelector(s);
    if (el && el.innerText.trim().length > 2) {
      result.salary = el.innerText.trim().split("\n")[0];
      break;
    }
  }

  // 4. Description
  const descSelectors = ["#job-description", ".job-description", "#description", "[data-automation-id='jobDescription']", "article", ".description"];
  for (const s of descSelectors) {
    const el = document.querySelector(s);
    if (el && el.innerText.trim().length > 20) {
      result.description = el.innerText.trim();
      break;
    }
  }

  // 5. Requirements
  const reqSelectors = ["#job-requirements", ".job-requirements", "#requirements", "#qualifications", "[class*='requirement']"];
  for (const s of reqSelectors) {
    const el = document.querySelector(s);
    if (el && el.innerText.trim().length > 10) {
      result.requirements = el.innerText.trim();
      break;
    }
  }

  // 6. Recruiter Email
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

  // 7. Application link
  const appLink = document.querySelector("#application-link, a[class*='apply'], a.btn-apply, a[href*='apply']");
  if (appLink && appLink.href) {
    result.application_link = appLink.href;
  }

  // 8. General text fallback if description is empty or minimal
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
