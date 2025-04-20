document.addEventListener("DOMContentLoaded", function() {
  // DOM Elements
  const pdfViewer = document.getElementById("pdfViewer");
  const contentPreview = document.getElementById("contentPreview");
  const toggleViewBtn = document.getElementById("toggleView");
  const downloadPdfBtn = document.getElementById("downloadPdf");
  const generatePdfBtn = document.getElementById("generatePdfBtn");
  const loadingOverlay = document.getElementById("loadingOverlay");
  const loadingMessage = document.getElementById("loadingMessage");

  // Toggle between PDF viewer and content preview
  toggleViewBtn.addEventListener("click", function() {
    if (pdfViewer.style.display === "none") {
      pdfViewer.style.display = "block";
      contentPreview.style.display = "none";
      toggleViewBtn.innerHTML = '<i class="fas fa-list-alt me-1"></i> Show Content';
    } else {
      pdfViewer.style.display = "none";
      contentPreview.style.display = "block";
      toggleViewBtn.innerHTML = '<i class="fas fa-file-pdf me-1"></i> Show PDF';
    }
  });

  // Download PDF
  downloadPdfBtn.addEventListener("click", function() {
    const iframe = pdfViewer.querySelector("iframe");
    if (iframe && iframe.src) {
      try {
        // Create a temporary link to download the PDF
        const link = document.createElement("a");
        link.href = iframe.src;
        link.download = document.title.replace(" - AI Research Assistant", "") + ".pdf";
        link.target = "_blank";
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
      } catch (error) {
        console.error("Error downloading PDF:", error);
        alert("Error downloading PDF: " + error.message);
      }
    } else {
      alert("Please generate the PDF first.");
    }
  });

  // Show loading when generating PDF
  if (generatePdfBtn) {
    generatePdfBtn.addEventListener("click", function() {
      showLoading("Generating PDF. This may take a minute...");
    });
  }

  // Handle iframe load event to hide loading overlay
  const iframe = pdfViewer.querySelector("iframe");
  if (iframe) {
    iframe.addEventListener("load", function() {
      hideLoading();
      // Enable download button once PDF is loaded
      downloadPdfBtn.disabled = false;
    });
    
    // Add error handling for iframe loading
    iframe.addEventListener("error", function(e) {
      console.error("Error loading PDF in iframe:", e);
      hideLoading();
      alert("Error loading PDF. Please try generating it again.");
    });
  }

  // Show loading overlay
  function showLoading(message) {
    loadingMessage.textContent = message || "Loading...";
    loadingOverlay.style.display = "flex";
  }

  // Hide loading overlay
  function hideLoading() {
    loadingOverlay.style.display = "none";
  }

  // Initialize the page
  if (iframe && iframe.src) {
    showLoading("Loading PDF...");
  }
});

// Toggle content preview expansion
function toggleContentPreview(element) {
  element.classList.toggle("expanded");
}