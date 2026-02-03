// content/content-script.js

class PageContentExtractor {
  constructor() {
    this.setupMessageListener();
  }

  setupMessageListener() {
    chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
      if (request.action === "extractPageContent") {
        this.extractContent().then(sendResponse);
        return true; // Keep channel open for async response
      }
    });
  }

  async extractContent() {
    const content = {
      url: window.location.href,
      title: document.title,
      text: this.extractText(),
      links: this.extractLinks(),
      images: this.extractImages(),
      forms: this.extractForms(),
      tables: this.extractTables(),
      metadata: this.extractMetadata(),
      timestamp: new Date().toISOString(),
    };

    return content;
  }

  extractText() {
    // Remove script and style elements
    const clone = document.cloneNode(true);
    const scripts = clone.querySelectorAll(
      "script, style, nav, footer, header, aside"
    );
    scripts.forEach((el) => el.remove());

    // Try to find main content
    const mainSelectors = [
      "main",
      "article",
      '[role="main"]',
      ".main-content",
      ".content",
      ".post-content",
      ".entry-content",
      "#main",
      "#content",
      "#main-content",
    ];

    let mainContent = null;
    for (const selector of mainSelectors) {
      mainContent = clone.querySelector(selector);
      if (mainContent) break;
    }

    const textElement = mainContent || clone.body || clone.documentElement;
    let text = textElement.innerText || textElement.textContent || "";

    // Clean up text: remove excessive whitespace
    text = text.replace(/\s+/g, " ").trim();

    // Limit text size
    if (text.length > 50000) {
      text = text.substring(0, 50000) + "... [truncated]";
    }

    return text;
  }

  extractLinks() {
    const links = [];
    document.querySelectorAll("a[href]").forEach((link) => {
      if (links.length < 50) {
        links.push({
          text: link.innerText.trim(),
          url: link.href,
          title: link.title || "",
        });
      }
    });
    return links;
  }

  extractImages() {
    const images = [];
    document.querySelectorAll("img[src]").forEach((img) => {
      if (images.length < 20) {
        images.push({
          src: img.src,
          alt: img.alt || "",
          title: img.title || "",
        });
      }
    });
    return images;
  }

  extractForms() {
    const forms = [];
    document.querySelectorAll("form").forEach((form) => {
      const inputs = [];
      form.querySelectorAll("input, textarea, select").forEach((input) => {
        inputs.push({
          type: input.type || input.tagName.toLowerCase(),
          name: input.name || "",
          placeholder: input.placeholder || "",
          label: this.getLabelFor(input),
        });
      });
      forms.push({
        action: form.action || "",
        method: form.method || "get",
        inputs: inputs,
      });
    });
    return forms;
  }

  getLabelFor(input) {
    const id = input.id;
    if (id) {
      const label = document.querySelector(`label[for="${id}"]`);
      if (label) return label.innerText.trim();
    }
    // Try to find parent label
    const parentLabel = input.closest("label");
    if (parentLabel) return parentLabel.innerText.trim();
    return "";
  }

  extractTables() {
    const tables = [];
    document.querySelectorAll("table").forEach((table) => {
      const rows = [];
      table.querySelectorAll("tr").forEach((tr) => {
        const cells = [];
        tr.querySelectorAll("td, th").forEach((cell) => {
          cells.push(cell.innerText.trim());
        });
        if (cells.length > 0) rows.push(cells);
      });
      if (rows.length > 0) tables.push(rows);
    });
    return tables.slice(0, 10); // Limit to 10 tables
  }

  extractMetadata() {
    const meta = {};

    // Extract meta tags
    document.querySelectorAll("meta").forEach((metaTag) => {
      const name =
        metaTag.getAttribute("name") ||
        metaTag.getAttribute("property") ||
        metaTag.getAttribute("itemprop");
      const content = metaTag.getAttribute("content");
      if (name && content) {
        meta[name] = content;
      }
    });

    // Extract structured data (JSON-LD)
    document
      .querySelectorAll('script[type="application/ld+json"]')
      .forEach((script) => {
        try {
          const data = JSON.parse(script.textContent);
          if (!meta.structuredData) {
            meta.structuredData = [];
          }
          meta.structuredData.push(data);
        } catch (e) {
          // Ignore parse errors
        }
      });

    return meta;
  }
}

// Initialize when script loads
if (document.readyState === "loading") {
  document.addEventListener("DOMContentLoaded", () => {
    new PageContentExtractor();
  });
} else {
  new PageContentExtractor();
}
