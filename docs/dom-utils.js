(function () {
  function clearElement(el) {
    while (el.firstChild) {
      el.removeChild(el.firstChild);
    }
  }

  function createSvgElement(svg) {
    const template = document.createElement("template");
    template.innerHTML = svg.trim();
    return template.content.firstElementChild;
  }

  function setIconLabel(el, svg, label) {
    clearElement(el);
    const icon = createSvgElement(svg);
    if (icon) el.appendChild(icon);
    if (label) {
      el.appendChild(document.createTextNode(" " + label));
    }
  }

  window.domUtils = { clearElement, createSvgElement, setIconLabel };
})();
