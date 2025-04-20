document.addEventListener("DOMContentLoaded", function () {
  // DOM Elements
  const loadingOverlay = document.getElementById("loadingOverlay");
  const loadingMessage = document.getElementById("loadingMessage");
  const outlineFormContainer = document.getElementById("outlineFormContainer");
  const outlineDetailContainer = document.getElementById("outlineDetailContainer");

  // Buttons
  const generateOutlineBtn = document.getElementById("generateOutlineBtn");
  const viewOutlineBtn = document.getElementById("viewOutlineBtn");
  const approveOutlineBtn = document.getElementById("approveOutlineBtn");
  const regenerateOutlineBtn = document.getElementById("regenerateOutlineBtn");
  const closeOutlineForm = document.getElementById("closeOutlineForm");
  const closeOutlineDetail = document.getElementById("closeOutlineDetail");
  const cancelOutlineGeneration = document.getElementById("cancelOutlineGeneration");
  const approveOutlineFromDetail = document.getElementById("approveOutlineFromDetail");
  const generateAllContentBtn = document.getElementById("generateAllContentBtn");
  const refreshProgressBtn = document.getElementById("refreshProgressBtn");

  // Progress elements
  const wordProgressBar = document.getElementById("wordProgressBar");
  const sectionProgressBar = document.getElementById("sectionProgressBar");

  // Forms
  const outlineGenerationForm = document.getElementById("outlineGenerationForm");

  // Content generation buttons
  const generateContentBtns = document.querySelectorAll(".generate-content-btn");

  // Content previews
  const contentPreviews = document.querySelectorAll(".content-preview");

  // Show loading overlay
  function showLoading(message) {
    loadingMessage.textContent = message || "Processing your request...";
    loadingOverlay.classList.add("active");
  }

  // Hide loading overlay
  function hideLoading() {
    loadingOverlay.classList.remove("active");
  }

  // Show outline form
  function showOutlineForm() {
    outlineFormContainer.classList.add("active");
    if (outlineDetailContainer) {
      outlineDetailContainer.classList.remove("active");
    }
  }

  // Hide outline form
  function hideOutlineForm() {
    outlineFormContainer.classList.remove("active");
  }

  // Show outline detail
  function showOutlineDetail() {
    if (outlineDetailContainer) {
      outlineDetailContainer.classList.add("active");
      outlineFormContainer.classList.remove("active");
    }
  }

  // Hide outline detail
  function hideOutlineDetail() {
    if (outlineDetailContainer) {
      outlineDetailContainer.classList.remove("active");
    }
  }

  // Generate outline
  async function generateOutline(event) {
    event.preventDefault();

    const projectId = outlineGenerationForm.dataset.projectId;
    const complexity = document.getElementById("complexity").value;
    const totalPages = document.getElementById("total_pages").value;

    const formData = new FormData();
    formData.append("complexity", complexity);
    formData.append("total_pages", totalPages);

    showLoading("Generating research outline. This may take a minute...");

    try {
      const response = await fetch(`/projects/${projectId}/generate-outline`, {
        method: "POST",
        body: formData,
        headers: {
          "X-Requested-With": "XMLHttpRequest",
        },
      });

      if (!response.ok) {
        throw new Error(`HTTP error! Status: ${response.status}`);
      }

      const result = await response.json();

      if (result.success) {
        // Reload the page to show the new outline
        window.location.reload();
      } else {
        hideLoading();
        alert("Error generating outline: " + (result.error || "Unknown error"));
      }
    } catch (error) {
      hideLoading();
      console.error("Error generating outline:", error);
      alert("An error occurred while generating the outline. Please try again.");
    }
  }

  // Approve outline
  async function approveOutline(outlineId) {
    showLoading("Approving outline...");

    try {
      const response = await fetch(`/outlines/${outlineId}`, {
        method: "POST",
        headers: {
          "X-Requested-With": "XMLHttpRequest",
          "Content-Type": "application/json",
        },
      });

      if (!response.ok) {
        throw new Error(`HTTP error! Status: ${response.status}`);
      }

      const result = await response.json();

      if (result.success) {
        // Reload the page to show the approved outline
        window.location.reload();
      } else {
        hideLoading();
        alert("Error approving outline: " + (result.error || "Unknown error"));
      }
    } catch (error) {
      hideLoading();
      console.error("Error approving outline:", error);
      alert("An error occurred while approving the outline. Please try again.");
    }
  }

  // Generate content
  async function generateContent(projectId, sectionTitle) {
    showLoading(`Generating content for "${sectionTitle}". This may take a few minutes...`);

    try {
      const response = await fetch(`/projects/${projectId}/generate-content/${encodeURIComponent(sectionTitle)}`, {
        method: "POST",
        headers: {
          "X-Requested-With": "XMLHttpRequest",
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          section_title: sectionTitle,
          page_by_page: true,
        }),
      });

      if (!response.ok) {
        throw new Error(`HTTP error! Status: ${response.status}`);
      }

      const result = await response.json();

      if (result.success) {
        // Reload the page to show the new content
        window.location.reload();
      } else {
        hideLoading();
        alert("Error generating content: " + (result.error || "Unknown error"));
      }
    } catch (error) {
      hideLoading();
      console.error("Error generating content:", error);
      alert("An error occurred while generating content. Please try again.");
    }
  }

  // Generate all content
  async function generateAllContent(projectId) {
    showLoading("Starting content generation for all sections...");

    try {
      const response = await fetch(`/projects/${projectId}/generate-all-content`, {
        method: "POST",
        headers: {
          "X-Requested-With": "XMLHttpRequest",
          "Content-Type": "application/json",
        },
      });

      if (!response.ok) {
        throw new Error(`HTTP error! Status: ${response.status}`);
      }

      const result = await response.json();

      if (result.success) {
        // Don't hide loading yet - keep it visible during generation
        
        // Start generating content for each section sequentially
        const sections = result.sections;
        
        if (sections.length > 0) {
          // Keep the loading overlay active but update the message
          loadingMessage.textContent = `Generating content for "${sections[0]}"... (1/${sections.length})`;
          
          // Generate the first section
          await generateNextSection(projectId, sections, 0);
        } else {
          hideLoading();
          // Refresh the page if all sections are already generated
          window.location.reload();
        }
        
        // Set up polling for progress updates
        startProgressPolling(projectId);
      } else {
        hideLoading();
        alert("Error starting content generation: " + (result.error || "Unknown error"));
      }
    } catch (error) {
      hideLoading();
      console.error("Error starting content generation:", error);
      alert("An error occurred while starting content generation. Please try again.");
    }
  }

  // Generate sections one by one
  async function generateNextSection(projectId, sections, currentIndex) {
    if (currentIndex >= sections.length) {
      // All sections generated, reload the page
      hideLoading();
      window.location.reload();
      return;
    }

    const sectionTitle = sections[currentIndex];
    loadingMessage.textContent = `Generating content for "${sectionTitle}"... (${currentIndex + 1}/${sections.length})`;

    try {
      const response = await fetch(`/projects/${projectId}/generate-content/${encodeURIComponent(sectionTitle)}`, {
        method: "POST",
        headers: {
          "X-Requested-With": "XMLHttpRequest",
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          section_title: sectionTitle,
          page_by_page: true,
        }),
      });

      if (!response.ok) {
        throw new Error(`HTTP error! Status: ${response.status}`);
      }

      const result = await response.json();

      if (result.success) {
        // Update progress
        updateContentProgress(projectId);
        
        // Move to the next section
        setTimeout(() => {
          generateNextSection(projectId, sections, currentIndex + 1);
        }, 1000); // Small delay between sections
      } else {
        console.error("Error generating content for section:", sectionTitle, result.error);
        // Continue with next section even if this one failed
        setTimeout(() => {
          generateNextSection(projectId, sections, currentIndex + 1);
        }, 1000);
      }
    } catch (error) {
      console.error("Error generating content for section:", sectionTitle, error);
      // Continue with next section even if this one failed
      setTimeout(() => {
        generateNextSection(projectId, sections, currentIndex + 1);
      }, 1000);
    }
  }

  // Update progress bars
  function updateProgressBars(data) {
    if (wordProgressBar) {
      const wordPercentage = data.word_percentage.toFixed(1);
      wordProgressBar.style.width = `${wordPercentage}%`;
      wordProgressBar.textContent = `${data.total_words} words / ${data.target_words} target`;
    }

    if (sectionProgressBar) {
      const sectionPercentage = data.progress_percentage.toFixed(1);
      sectionProgressBar.style.width = `${sectionPercentage}%`;
      sectionProgressBar.textContent = `${data.completed_sections} / ${data.total_sections} sections completed`;
    }
  }

  // Poll for progress updates
  let progressPollingInterval = null;

  function startProgressPolling(projectId) {
    // Clear any existing polling
    if (progressPollingInterval) {
      clearInterval(progressPollingInterval);
    }

    // Initial update
    updateContentProgress(projectId);

    // Set up polling every 5 seconds
    progressPollingInterval = setInterval(() => {
      updateContentProgress(projectId);
    }, 5000);
  }

  // Update content progress
  async function updateContentProgress(projectId) {
    try {
      const response = await fetch(`/projects/${projectId}/content-status`, {
        headers: {
          "X-Requested-With": "XMLHttpRequest",
        },
      });

      if (!response.ok) {
        throw new Error(`HTTP error! Status: ${response.status}`);
      }

      const result = await response.json();

      if (result.success) {
        updateProgressBars(result);
        
        // If all sections are complete, stop polling
        if (result.completed_sections >= result.total_sections) {
          if (progressPollingInterval) {
            clearInterval(progressPollingInterval);
            progressPollingInterval = null;
          }
          
          // Reload the page to show all content
          window.location.reload();
        }
      }
    } catch (error) {
      console.error("Error updating content progress:", error);
      // Don't stop polling on error
    }
  }

  // Toggle content preview
  function toggleContentPreview(element) {
    element.classList.toggle("expanded");
  }

  // Event Listeners
  if (generateOutlineBtn) {
    generateOutlineBtn.addEventListener("click", showOutlineForm);
  }

  if (viewOutlineBtn) {
    viewOutlineBtn.addEventListener("click", showOutlineDetail);
  }

  if (closeOutlineForm) {
    closeOutlineForm.addEventListener("click", hideOutlineForm);
  }

  if (closeOutlineDetail) {
    closeOutlineDetail.addEventListener("click", hideOutlineDetail);
  }

  if (cancelOutlineGeneration) {
    cancelOutlineGeneration.addEventListener("click", hideOutlineForm);
  }

  if (outlineGenerationForm) {
    outlineGenerationForm.addEventListener("submit", generateOutline);
  }

  if (approveOutlineBtn) {
    approveOutlineBtn.addEventListener("click", function () {
      const outlineId = this.dataset.outlineId;
      approveOutline(outlineId);
    });
  }

  if (approveOutlineFromDetail) {
    approveOutlineFromDetail.addEventListener("click", function () {
      const outlineId = this.dataset.outlineId;
      approveOutline(outlineId);
    });
  }

  if (regenerateOutlineBtn) {
    regenerateOutlineBtn.addEventListener("click", showOutlineForm);
  }

  if (generateAllContentBtn) {
    generateAllContentBtn.addEventListener("click", function() {
      const projectId = this.dataset.projectId;
      generateAllContent(projectId);
    });
  }

  if (refreshProgressBtn) {
    refreshProgressBtn.addEventListener("click", function() {
      const projectId = generateAllContentBtn.dataset.projectId;
      updateContentProgress(projectId);
    });
  }

  // Add event listeners to all content generation buttons
  generateContentBtns.forEach(function (btn) {
    btn.addEventListener("click", function () {
      const projectId = this.dataset.projectId;
      const sectionTitle = this.dataset.sectionTitle;
      generateContent(projectId, sectionTitle);
    });
  });

  // Add event listeners to all content previews
  contentPreviews.forEach(function (preview) {
    preview.addEventListener("click", function () {
      toggleContentPreview(this);
    });
  });

  // Check if we need to start progress polling on page load
  if (generateAllContentBtn) {
    const projectId = generateAllContentBtn.dataset.projectId;
    updateContentProgress(projectId);
  }
});
