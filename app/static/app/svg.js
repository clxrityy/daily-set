const SVG_NS = "http://www.w3.org/2000/svg";
const __svgPatternRegistry = {};

function ensureSharedDefs() {
  let holder = document.getElementById("__svg_defs_holder");
  if (!holder) {
    holder = document.createElementNS(SVG_NS, "svg");
    holder.setAttribute("id", "__svg_defs_holder");
    holder.style.position = "absolute";
    holder.style.width = "0";
    holder.style.height = "0";
    holder.style.overflow = "hidden";
    document.body.appendChild(holder);
  }
  let defs = holder.querySelector("defs");
  if (!defs) {
    defs = document.createElementNS(SVG_NS, "defs");
    holder.appendChild(defs);
  }
  return defs;
}

export function getOrCreateStripedPattern(color) {
  const key = `stripe-${color}`;
  if (__svgPatternRegistry[key]) return __svgPatternRegistry[key];
  const defs = ensureSharedDefs();
  const pattern = document.createElementNS(SVG_NS, "pattern");
  const id = `p-${Math.random().toString(36).slice(2, 8)}`;
  pattern.setAttribute("id", id);
  pattern.setAttribute("patternUnits", "userSpaceOnUse");
  pattern.setAttribute("width", "10");
  pattern.setAttribute("height", "10");
  const path = document.createElementNS(SVG_NS, "path");
  path.setAttribute("d", "M0,10 L10,0");
  path.setAttribute("stroke", color);
  path.setAttribute("stroke-width", "3");
  pattern.appendChild(path);
  defs.appendChild(pattern);
  __svgPatternRegistry[key] = id;
  return id;
}

export function colorForIndex(i) {
  const cols = ["#ef4444", "#10b981", "#7c3aed"];
  return cols[i % cols.length] || "#000";
}

export function createSymbolSVG(shape, colorIdx, shading) {
  const color = colorForIndex(colorIdx);
  const svg = document.createElementNS(SVG_NS, "svg");
  svg.setAttribute("viewBox", "0 0 100 100");
  svg.setAttribute("role", "img");

  if (shading === 1) {
    const pid = getOrCreateStripedPattern(color);
    svg._patternId = pid;
  }

  let shapeEl;
  if (shape === 0) {
    shapeEl = document.createElementNS(SVG_NS, "ellipse");
    shapeEl.setAttribute("cx", "50");
    shapeEl.setAttribute("cy", "50");
    shapeEl.setAttribute("rx", "30");
    shapeEl.setAttribute("ry", "18");
  } else if (shape === 1) {
    shapeEl = document.createElementNS(SVG_NS, "polygon");
    shapeEl.setAttribute("points", "50,18 78,50 50,82 22,50");
  } else {
    shapeEl = document.createElementNS(SVG_NS, "path");
    shapeEl.setAttribute(
      "d",
      "M20,30 A20,20 0 0,1 50,30 A20,20 0 0,1 80,30 Q80,60 50,85 Q20,60 20,30 Z"
    );
  }

  if (shading === 0) {
    shapeEl.setAttribute("fill", color);
    shapeEl.setAttribute("stroke", color);
  } else if (shading === 1) {
    const pid = svg._patternId;
    if (pid) shapeEl.setAttribute("fill", `url(#${pid})`);
    shapeEl.setAttribute("stroke", color);
  } else {
    shapeEl.setAttribute("fill", "none");
    shapeEl.setAttribute("stroke", color);
    shapeEl.setAttribute("stroke-width", "3");
  }

  shapeEl.setAttribute("stroke-linejoin", "round");
  shapeEl.setAttribute("stroke-linecap", "round");
  svg.appendChild(shapeEl);
  return svg;
}
