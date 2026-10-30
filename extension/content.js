/**
 * JobShield AI — Generic DOM-based Job Information Extractor
 * Extracts job posting attributes with sensible semantic and generic fallbacks.
 */

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
      // Avoid accidentally capturing huge text containers
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
      result.salary = el.innerText.trim().split("\n")[0];
      break;
    }
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

  // If email not found explicitly, search entire document text
  if (!result.recruiter_email) {
    const bodyText = document.body ? document.body.innerText : "";
    const emailMatches = bodyText.match(/[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+/g);
    if (emailMatches && emailMatches.length > 0) {
      // Pick first non-image / non-asset email
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
    return true; // Keep channel open for async response
  });
}
