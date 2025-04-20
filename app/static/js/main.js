// Wait for the DOM to be fully loaded
document.addEventListener("DOMContentLoaded", function () {
  // Auto-dismiss alerts after 5 seconds
  const alerts = document.querySelectorAll(".alert:not(.alert-permanent)");
  alerts.forEach(function (alert) {
    setTimeout(function () {
      const closeButton = alert.querySelector(".btn-close");
      if (closeButton) {
        closeButton.click();
      }
    }, 5000);
  });

  // Enable tooltips
  const tooltipTriggerList = [].slice.call(
    document.querySelectorAll('[data-bs-toggle="tooltip"]')
  );
  tooltipTriggerList.map(function (tooltipTriggerEl) {
    return new bootstrap.Tooltip(tooltipTriggerEl);
  });

  // Add smooth scrolling to all links
  document.querySelectorAll('a[href^="#"]').forEach((anchor) => {
    anchor.addEventListener("click", function (e) {
      e.preventDefault();

      const targetId = this.getAttribute("href");
      if (targetId === "#") return;

      const targetElement = document.querySelector(targetId);
      if (targetElement) {
        targetElement.scrollIntoView({
          behavior: "smooth",
          block: "start",
        });
      }
    });
  });

  // Expand content preview on click
  const contentPreviews = document.querySelectorAll(".content-preview");
  contentPreviews.forEach((preview) => {
    preview.addEventListener("click", function () {
      if (this.style.maxHeight === "200px" || this.style.maxHeight === "") {
        this.style.maxHeight = "600px";
        this.style.cursor = "zoom-out";
      } else {
        this.style.maxHeight = "200px";
        this.style.cursor = "zoom-in";
      }
    });

    // Add zoom-in cursor by default
    preview.style.cursor = "zoom-in";
  });
});
