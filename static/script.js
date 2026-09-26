// ==========================================
// DOCSHIELD AI - MAIN SCRIPT
// STEP 46 - VERIFICATION + HISTORY + DASHBOARD
// ==========================================

let lastVerification = null;
let currentScanId = null;

let riskChart = null;
let completeHistory = [];
let currentRiskFilter = "all";


// ==========================================
// SECTION NAVIGATION
// ==========================================

function hideAllSections() {

    const dashboard =
        document.getElementById("dashboardSection");

    const verify =
        document.getElementById("verifySection");

    const history =
        document.getElementById("historySection");

    if (dashboard) {
        dashboard.classList.add("hidden");
    }

    if (verify) {
        verify.classList.add("hidden");
    }

    if (history) {
        history.classList.add("hidden");
    }
}


// ==========================================
// SHOW DASHBOARD
// ==========================================

function showDashboard() {

    hideAllSections();

    const dashboard =
        document.getElementById("dashboardSection");

    if (dashboard) {
        dashboard.classList.remove("hidden");
    }

    loadStatistics();
}


// ==========================================
// SHOW VERIFY
// ==========================================

function showVerify() {

    hideAllSections();

    const verify =
        document.getElementById("verifySection");

    if (verify) {
        verify.classList.remove("hidden");
    }
}


// ==========================================
// SHOW HISTORY
// ==========================================

function showHistory() {

    hideAllSections();

    const history =
        document.getElementById("historySection");

    if (history) {
        history.classList.remove("hidden");
    }

    loadHistory();
}


// ==========================================
// ANALYSIS STATUS
// ==========================================

function applyAnalysisStatus(element, value) {

    if (!element) {
        return;
    }

    element.classList.remove(
        "analysis-passed",
        "analysis-review",
        "analysis-risk"
    );

    const status =
        String(value || "").toLowerCase();

    if (
        status.includes("passed") ||
        status.includes("completed") ||
        status.includes("good") ||
        status.includes("normal")
    ) {

        element.classList.add(
            "analysis-passed"
        );

    }

    else if (
        status.includes("risk") ||
        status.includes("failed") ||
        status.includes("suspicious")
    ) {

        element.classList.add(
            "analysis-risk"
        );

    }

    else {

        element.classList.add(
            "analysis-review"
        );
    }
}


// ==========================================
// UPDATE VERIFICATION SUMMARY
// ==========================================

function updateVerificationSummary(data) {

    if (!data) {
        return;
    }

    const summaryElements = {

        summaryFilename:
            data.filename || "",

        summaryRiskScore:
            data.risk_score ?? 0,

        summaryStatus:
            data.status || "",

        summaryDate:
            data.scan_time ||
            data.timestamp ||
            new Date().toLocaleString()

    };

    Object.keys(summaryElements).forEach(function(id) {

        const element =
            document.getElementById(id);

        if (element) {

            element.innerText =
                summaryElements[id];

        }

    });
}


// ==========================================
// UPDATE RISK CLASSIFICATION BANNER
// ==========================================

function updateRiskClassificationBanner(score) {

    const banner =
        document.getElementById(
            "riskClassificationBanner"
        );

    if (!banner) {
        return;
    }

    const riskScore =
        Number(score || 0);

    banner.classList.remove(
        "low-risk-banner",
        "medium-risk-banner",
        "high-risk-banner"
    );

    if (riskScore <= 30) {

        banner.innerText =
            "LOW RISK — Document appears safe";

        banner.classList.add(
            "low-risk-banner"
        );

    }

    else if (riskScore <= 60) {

        banner.innerText =
            "MEDIUM RISK — Document requires review";

        banner.classList.add(
            "medium-risk-banner"
        );

    }

    else {

        banner.innerText =
            "HIGH RISK — Suspicious document detected";

        banner.classList.add(
            "high-risk-banner"
        );

    }
}


// ==========================================
// SHOW VERIFICATION COMPLETE
// ==========================================

function showVerificationComplete(data) {

    const completeBox =
        document.getElementById(
            "verificationComplete"
        );

    if (!completeBox) {
        return;
    }

    completeBox.classList.remove("hidden");

    const completeStatus =
        document.getElementById(
            "completeStatus"
        );

    const completeScore =
        document.getElementById(
            "completeScore"
        );

    if (completeStatus) {

        completeStatus.innerText =
            data.status || "Verification completed";

    }

    if (completeScore) {

        completeScore.innerText =
            (data.risk_score ?? 0) + "/100";

    }
}


// ==========================================
// GENERATE REPORT
// ==========================================

function generateReport() {

    if (!currentScanId) {

        alert(
            "Please verify a document first."
        );

        return;
    }

    window.open(
        "/generate-report/" +
        currentScanId,
        "_blank"
    );
}


// ==========================================
// VERIFY DOCUMENT
// ==========================================

async function verifyDocument() {

    const input =
        document.getElementById(
            "documentInput"
        );

    if (
        !input ||
        !input.files ||
        input.files.length === 0
    ) {

        alert(
            "Please select a document first."
        );

        return;
    }

    const file =
        input.files[0];

    const formData =
        new FormData();

    formData.append(
        "document",
        file
    );

    const resultSection =
        document.getElementById(
            "resultSection"
        );

    const statusElement =
        document.getElementById(
            "status"
        );

    if (resultSection) {

        resultSection.classList.remove(
            "hidden"
        );

    }

    if (statusElement) {

        statusElement.innerText =
            "⏳ Screening document...";

    }

    try {

        const response =
            await fetch(
                "/verify",
                {
                    method: "POST",
                    body: formData
                }
            );

        const data =
            await response.json();

        if (!response.ok) {

            alert(
                data.error ||
                "Document verification failed."
            );

            return;
        }

        // ------------------------------------------
        // SAVE CURRENT VERIFICATION
        // ------------------------------------------

        lastVerification =
            data;

        currentScanId =
            data.id ||
            data.scan_id ||
            null;


        // ------------------------------------------
        // RISK SCORE
        // ------------------------------------------

        const score =
            Number(
                data.risk_score || 0
            );

        const riskScore =
            document.getElementById(
                "riskScore"
            );

        if (riskScore) {

            riskScore.innerText =
                score;

        }


        // ------------------------------------------
        // RISK PROGRESS
        // ------------------------------------------

        const riskProgress =
            document.getElementById(
                "riskProgress"
            );

        if (riskProgress) {

            riskProgress.style.width =
                score + "%";

            if (score <= 30) {

                riskProgress.style.background =
                    "#22c55e";

            }

            else if (score <= 60) {

                riskProgress.style.background =
                    "#f59e0b";

            }

            else {

                riskProgress.style.background =
                    "#ef4444";

            }

        }


        // ------------------------------------------
        // RISK CIRCLE
        // ------------------------------------------

        const riskCircle =
            document.querySelector(
                ".risk-circle"
            );

        if (riskCircle) {

            riskCircle.classList.remove(
                "low-circle",
                "medium-circle",
                "high-circle"
            );

            if (score <= 30) {

                riskCircle.classList.add(
                    "low-circle"
                );

            }

            else if (score <= 60) {

                riskCircle.classList.add(
                    "medium-circle"
                );

            }

            else {

                riskCircle.classList.add(
                    "high-circle"
                );

            }

        }


        // ------------------------------------------
        // RISK LABEL
        // ------------------------------------------

        const riskLabel =
            document.getElementById(
                "riskLabel"
            );

        if (riskLabel) {

            riskLabel.classList.remove(
                "low-risk",
                "medium-risk",
                "high-risk"
            );

            if (score <= 30) {

                riskLabel.innerText =
                    "LOW RISK";

                riskLabel.classList.add(
                    "low-risk"
                );

            }

            else if (score <= 60) {

                riskLabel.innerText =
                    "MEDIUM RISK";

                riskLabel.classList.add(
                    "medium-risk"
                );

            }

            else {

                riskLabel.innerText =
                    "HIGH RISK";

                riskLabel.classList.add(
                    "high-risk"
                );

            }

        }


        // ------------------------------------------
        // STATUS
        // ------------------------------------------

        if (statusElement) {

            statusElement.innerText =
                data.status || "Verification completed";

        }


        // ------------------------------------------
        // VERIFICATION SUMMARY
        // ------------------------------------------

        updateVerificationSummary(
            data
        );


        // ------------------------------------------
        // RISK CLASSIFICATION BANNER
        // ------------------------------------------

        updateRiskClassificationBanner(
            score
        );


        // ------------------------------------------
        // VERIFICATION COMPLETE
        // ------------------------------------------

        showVerificationComplete(
            data
        );


        // ------------------------------------------
        // AI ANALYSIS
        // ------------------------------------------

        if (data.analysis) {

            const analysisMap = {

                ocr: "ocr",

                structure: "structure",

                image: "image",

                text: "text",

                tampering: "tampering"

            };

            Object.keys(
                analysisMap
            ).forEach(function(key) {

                const element =
                    document.getElementById(
                        analysisMap[key]
                    );

                if (!element) {
                    return;
                }

                const value =
                    data.analysis[key] ||
                    "Waiting";

                element.innerText =
                    value;

                applyAnalysisStatus(
                    element,
                    value
                );

            });

        }


        // ------------------------------------------
        // RISK REASONS
        // ------------------------------------------

        const reasonsElement =
            document.getElementById(
                "reasons"
            );

        if (reasonsElement) {

            reasonsElement.innerHTML =
                "";

            if (
                data.reasons &&
                data.reasons.length > 0
            ) {

                data.reasons.forEach(
                    function(reason) {

                        const li =
                            document.createElement(
                                "li"
                            );

                        li.innerText =
                            reason;

                        reasonsElement.appendChild(
                            li
                        );

                    }
                );

            }

            else {

                const li =
                    document.createElement(
                        "li"
                    );

                li.innerText =
                    "No major risk indicators detected.";

                reasonsElement.appendChild(
                    li
                );

            }

        }


        // ------------------------------------------
        // OCR TEXT
        // ------------------------------------------

        const extractedText =
            document.getElementById(
                "extractedText"
            );

        if (extractedText) {

            extractedText.value =
                data.extracted_text ||
                "No readable text detected.";

        }


        // ------------------------------------------
        // REFRESH DASHBOARD + HISTORY
        // ------------------------------------------

        await loadStatistics();

        await loadHistory();


        // ------------------------------------------
        // SCROLL TO RESULT
        // ------------------------------------------

        if (resultSection) {

            resultSection.scrollIntoView({
                behavior: "smooth",
                block: "start"
            });

        }

    }

    catch (error) {

        console.error(
            "Verification Error:",
            error
        );

        alert(
            "Unable to connect to DocShield AI server."
        );

    }

}


// ==========================================
// RISK CLASSIFICATION
// ==========================================

function getRiskClassification(score) {

    const riskScore =
        Number(score);

    if (riskScore <= 30) {

        return "LOW RISK";

    }

    if (riskScore <= 60) {

        return "MEDIUM RISK";

    }

    return "HIGH RISK";
}


// ==========================================
// RISK CSS CLASS
// ==========================================

function getRiskClass(score) {

    const riskScore =
        Number(score);

    if (riskScore <= 30) {

        return "history-low";

    }

    if (riskScore <= 60) {

        return "history-medium";

    }

    return "history-high";
}


// ==========================================
// UPDATE HISTORY TABLE HEADER
// ==========================================

function updateHistoryTableHeader() {

    const tableBody =
        document.getElementById(
            "historyTable"
        );

    if (!tableBody) {
        return;
    }

    const table =
        tableBody.closest("table");

    if (!table) {
        return;
    }

    const header =
        table.querySelector(
            "thead tr"
        );

    if (!header) {
        return;
    }

    header.innerHTML = `

        <th>Scan ID</th>

        <th>Document</th>

        <th>Risk Score</th>

        <th>Risk Classification</th>

        <th>Verification Status</th>

        <th>Date</th>

        <th>Action</th>

    `;
}


// ==========================================
// SEARCH TERM
// ==========================================

function getHistorySearchTerm() {

    const searchInput =
        document.getElementById(
            "historySearch"
        );

    if (!searchInput) {

        return "";

    }

    return searchInput.value
        .trim()
        .toLowerCase();
}


// ==========================================
// RISK FILTER
// ==========================================

function matchesRiskFilter(item) {

    const score =
        Number(
            item.risk_score || 0
        );

    if (
        currentRiskFilter === "high"
    ) {

        return score > 60;

    }

    if (
        currentRiskFilter === "medium"
    ) {

        return (
            score > 30 &&
            score <= 60
        );

    }

    if (
        currentRiskFilter === "low"
    ) {

        return score <= 30;

    }

    return true;
}


// ==========================================
// SEARCH FILTER
// ==========================================

function matchesSearch(
    item,
    searchTerm
) {

    if (!searchTerm) {

        return true;

    }

    const score =
        Number(
            item.risk_score || 0
        );

    const classification =
        getRiskClassification(
            score
        );

    const filename =
        item.filename || "";

    const status =
        item.status || "";

    const id =
        item.id || "";

    const date =
        item.timestamp ||
        item.scan_time ||
        "";

    const searchableText =

        String(id) +
        " " +
        String(filename) +
        " " +
        String(score) +
        " " +
        classification +
        " " +
        String(status) +
        " " +
        String(date);

    return searchableText
        .toLowerCase()
        .includes(searchTerm);
}


// ==========================================
// APPLY HISTORY FILTERS
// ==========================================

function applyHistoryFilters() {

    const searchTerm =
        getHistorySearchTerm();

    const filteredHistory =
        completeHistory.filter(
            function(item) {

                return (
                    matchesRiskFilter(item) &&
                    matchesSearch(
                        item,
                        searchTerm
                    )
                );

            }
        );

    renderHistory(
        filteredHistory
    );

    updateHistorySearchMessage(
        filteredHistory.length,
        completeHistory.length
    );
}


// ==========================================
// SET HISTORY FILTER
// ==========================================

function setHistoryFilter(filter) {

    currentRiskFilter =
        filter || "all";

    const buttons =
        document.querySelectorAll(
            ".history-filter-btn"
        );

    buttons.forEach(
        function(button) {

            button.classList.remove(
                "active"
            );

        }
    );

    let buttonId =
        "filterAll";

    if (
        currentRiskFilter === "high"
    ) {

        buttonId =
            "filterHigh";

    }

    else if (
        currentRiskFilter === "medium"
    ) {

        buttonId =
            "filterMedium";

    }

    else if (
        currentRiskFilter === "low"
    ) {

        buttonId =
            "filterLow";

    }

    const selectedButton =
        document.getElementById(
            buttonId
        );

    if (selectedButton) {

        selectedButton.classList.add(
            "active"
        );

    }

    applyHistoryFilters();
}


// ==========================================
// SEARCH RESULT MESSAGE
// ==========================================

function updateHistorySearchMessage(
    visibleCount,
    totalCount
) {

    const resultElement =
        document.getElementById(
            "historySearchResult"
        );

    if (!resultElement) {

        return;

    }

    const searchTerm =
        getHistorySearchTerm();

    let filterName =
        "";

    if (
        currentRiskFilter === "high"
    ) {

        filterName =
            "High Risk";

    }

    else if (
        currentRiskFilter === "medium"
    ) {

        filterName =
            "Medium Risk";

    }

    else if (
        currentRiskFilter === "low"
    ) {

        filterName =
            "Low Risk";

    }

    if (
        !searchTerm &&
        currentRiskFilter === "all"
    ) {

        resultElement.innerText =

            "Showing all " +
            totalCount +
            " verification record" +
            (
                totalCount === 1
                    ? ""
                    : "s"
            );

        return;
    }

    if (visibleCount === 0) {

        if (searchTerm) {

            resultElement.innerText =

                'No records found for "' +
                searchTerm +
                '"' +
                (
                    filterName
                        ? " in " + filterName
                        : ""
                ) +
                ".";

        }

        else {

            resultElement.innerText =

                "No " +
                filterName +
                " records found.";

        }

        return;
    }

    resultElement.innerText =

        "Showing " +
        visibleCount +
        " of " +
        totalCount +
        " verification record" +
        (
            totalCount === 1
                ? ""
                : "s"
        ) +
        (
            filterName
                ? " • " + filterName
                : ""
        );
}


// ==========================================
// CLEAR SEARCH
// ==========================================

function clearHistorySearch() {

    const input =
        document.getElementById(
            "historySearch"
        );

    if (input) {

        input.value =
            "";

    }

    applyHistoryFilters();

    if (input) {

        input.focus();

    }
}


// ==========================================
// INITIALIZE SEARCH
// ==========================================

function initializeHistorySearch() {

    const input =
        document.getElementById(
            "historySearch"
        );

    if (!input) {

        return;

    }

    input.addEventListener(
        "input",
        function() {

            applyHistoryFilters();

        }
    );
}


// ==========================================
// RENDER HISTORY
// ==========================================

function renderHistory(history) {

    const tableBody =
        document.getElementById(
            "historyTable"
        );

    if (!tableBody) {

        return;

    }

    updateHistoryTableHeader();

    tableBody.innerHTML =
        "";

    if (
        !history ||
        history.length === 0
    ) {

        tableBody.innerHTML = `

            <tr>

                <td colspan="7">

                    No verification history found.

                </td>

            </tr>

        `;

        return;
    }

    history.forEach(
        function(item) {

            const row =
                document.createElement(
                    "tr"
                );

            const score =
                Number(
                    item.risk_score || 0
                );

            const classification =
                getRiskClassification(
                    score
                );

            const riskClass =
                getRiskClass(
                    score
                );

            const status =
                item.status ||
                "Unknown";

            let statusClass =
                "history-status-review";

            const statusLower =
                String(
                    status
                ).toLowerCase();

            if (
                statusLower.includes("high") ||
                statusLower.includes("suspicious")
            ) {

                statusClass =
                    "history-status-danger";

            }

            else if (
                statusLower.includes("low") ||
                statusLower.includes("normal")
            ) {

                statusClass =
                    "history-status-safe";

            }

            row.innerHTML = `

                <td>
                    <strong>
                        #${escapeHTML(item.id)}
                    </strong>
                </td>

                <td>
                    <span class="history-filename">
                        ${escapeHTML(item.filename)}
                    </span>
                </td>

                <td>
                    <strong>
                        ${score}/100
                    </strong>
                </td>

                <td>
                    <span
                        class="history-risk-badge ${riskClass}">
                        ${classification}
                    </span>
                </td>

                <td>
                    <span
                        class="history-status-badge ${statusClass}">
                        ${escapeHTML(status)}
                    </span>
                </td>

                <td>
                    ${escapeHTML(
                        item.timestamp ||
                        item.scan_time ||
                        ""
                    )}
                </td>

                <td>

                    <button
                        class="delete-history-btn"
                        onclick="deleteVerificationRecord(${Number(item.id)})"
                        title="Delete this verification record">

                        🗑️ Delete

                    </button>

                </td>

            `;

            tableBody.appendChild(
                row
            );

        }
    );
}


// ==========================================
// DELETE ONE VERIFICATION RECORD
// ==========================================

async function deleteVerificationRecord(scanId) {

    if (!scanId) {

        return;

    }

    const confirmed =
        confirm(

            "Delete verification record #" +
            scanId +
            "?\n\n" +
            "The verification record, uploaded document and generated report will be permanently removed."

        );

    if (!confirmed) {

        return;

    }

    try {

        const response =
            await fetch(
                "/delete-scan/" +
                scanId,
                {
                    method: "DELETE"
                }
            );

        const data =
            await response.json();

        if (!response.ok) {

            alert(
                data.error ||
                "Could not delete the verification record."
            );

            return;
        }

        if (
            currentScanId !== null &&
            Number(currentScanId) ===
            Number(scanId)
        ) {

            currentScanId =
                null;

            lastVerification =
                null;

        }

        alert(
            "Verification record deleted successfully."
        );

        await loadHistory();

        await loadStatistics();

    }

    catch (error) {

        console.error(
            "Delete Record Error:",
            error
        );

        alert(
            "Unable to delete the verification record."
        );

    }
}


// ==========================================
// DELETE ALL HISTORY
// ==========================================

async function deleteAllHistory() {

    if (
        completeHistory.length === 0
    ) {

        alert(
            "There are no verification records to delete."
        );

        return;

    }

    const confirmed =
        confirm(

            "Delete ALL verification history?\n\n" +
            "This will permanently remove all verification records, uploaded documents and generated reports.\n\n" +
            "This action cannot be undone."

        );

    if (!confirmed) {

        return;

    }

    try {

        const response =
            await fetch(
                "/delete-all-history",
                {
                    method: "DELETE"
                }
            );

        const data =
            await response.json();

        if (!response.ok) {

            alert(
                data.error ||
                "Could not delete verification history."
            );

            return;

        }

        currentScanId =
            null;

        lastVerification =
            null;

        completeHistory =
            [];

        alert(

            data.deleted_count +
            " verification record" +
            (
                Number(data.deleted_count) === 1
                    ? ""
                    : "s"
            ) +
            " deleted successfully."

        );

        await loadHistory();

        await loadStatistics();

    }

    catch (error) {

        console.error(
            "Delete All Error:",
            error
        );

        alert(
            "Unable to delete verification history."
        );

    }
}


// ==========================================
// LOAD HISTORY
// ==========================================

async function loadHistory() {

    try {

        const response =
            await fetch(
                "/history"
            );

        const data =
            await response.json();

        completeHistory =
            data.history || [];

        applyHistoryFilters();

    }

    catch (error) {

        console.error(
            "History Error:",
            error
        );

    }
}


// ==========================================
// LOAD DASHBOARD STATISTICS
// ==========================================

async function loadStatistics() {

    try {

        const response =
            await fetch(
                "/history"
            );

        const data =
            await response.json();

        const history =
            data.history || [];

        let total =
            history.length;

        let high =
            0;

        let medium =
            0;

        let low =
            0;

        history.forEach(
            function(item) {

                const score =
                    Number(
                        item.risk_score || 0
                    );

                if (score > 60) {

                    high++;

                }

                else if (score > 30) {

                    medium++;

                }

                else {

                    low++;

                }

            }
        );

        const totalElement =
            document.getElementById(
                "totalScans"
            );

        const highElement =
            document.getElementById(
                "highRisk"
            );

        const mediumElement =
            document.getElementById(
                "mediumRisk"
            );

        const lowElement =
            document.getElementById(
                "lowRisk"
            );

        if (totalElement) {

            totalElement.innerText =
                total;

        }

        if (highElement) {

            highElement.innerText =
                high;

        }

        if (mediumElement) {

            mediumElement.innerText =
                medium;

        }

        if (lowElement) {

            lowElement.innerText =
                low;

        }


        // ==========================================
        // RISK CHART
        // ==========================================

        const canvas =
            document.getElementById(
                "riskChart"
            );

        if (
            canvas &&
            typeof Chart !== "undefined"
        ) {

            if (riskChart) {

                riskChart.destroy();

            }

            riskChart =
                new Chart(
                    canvas,
                    {

                        type: "bar",

                        data: {

                            labels: [
                                "High Risk",
                                "Medium Risk",
                                "Low Risk"
                            ],

                            datasets: [
                                {

                                    label:
                                        "Documents",

                                    data: [
                                        high,
                                        medium,
                                        low
                                    ],

                                    backgroundColor: [
                                        "#ef4444",
                                        "#f59e0b",
                                        "#22c55e"
                                    ],

                                    borderRadius: 8

                                }
                            ]

                        },

                        options: {

                            responsive: true,

                            maintainAspectRatio:
                                false,

                            plugins: {

                                legend: {

                                    display: false

                                }

                            },

                            scales: {

                                y: {

                                    beginAtZero: true,

                                    ticks: {

                                        precision: 0

                                    }

                                }

                            }

                        }

                    }
                );

        }

    }

    catch (error) {

        console.error(
            "Statistics Error:",
            error
        );

    }
}


// ==========================================
// ESCAPE HTML
// ==========================================

function escapeHTML(value) {

    if (
        value === null ||
        value === undefined
    ) {

        return "";

    }

    return String(value)

        .replace(
            /&/g,
            "&amp;"
        )

        .replace(
            /</g,
            "&lt;"
        )

        .replace(
            />/g,
            "&gt;"
        )

        .replace(
            /"/g,
            "&quot;"
        )

        .replace(
            /'/g,
            "&#039;"
        );

}


// ==========================================
// PAGE INITIALIZATION
// ==========================================

document.addEventListener(
    "DOMContentLoaded",
    function() {

        initializeHistorySearch();

        showDashboard();

        loadHistory();

    }
);