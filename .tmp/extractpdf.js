const fs = require("fs");
const zlib = require("zlib");

function inflateObjectStream(objs, id) {
  const body = objs[id];
  if (!body) return "";
  const si = body.indexOf("stream");
  if (si < 0) return "";
  let start = si + 6;
  if (body[start] === "\r" && body[start + 1] === "\n") start += 2;
  else if (body[start] === "\n") start += 1;
  const end = body.indexOf("endstream", start);
  const raw = Buffer.from(body.slice(start, end), "latin1");
  try {
    return zlib.inflateSync(raw).toString("latin1");
  } catch {
    return raw.toString("latin1");
  }
}

function decodePdf(path) {
  const bytes = fs.readFileSync(path);
  const pdf = bytes.toString("latin1");
  const objs = {};
  for (const match of pdf.matchAll(/(\d+)\s+0\s+obj([\s\S]*?)endobj/g)) {
    objs[match[1]] = match[2];
  }

  const cmaps = {};
  for (const id of Object.keys(objs)) {
    const stream = inflateObjectStream(objs, id);
    if (!stream.includes("beginbfchar")) continue;
    const map = {};
    for (const m of stream.matchAll(/<([0-9A-F]+)>\s+<([0-9A-F]+)>/g)) {
      if (m[1].length > 4) continue;
      let value = "";
      for (let i = 0; i < m[2].length; i += 4) {
        value += String.fromCodePoint(parseInt(m[2].slice(i, i + 4), 16));
      }
      map[m[1].toUpperCase()] = value;
    }
    cmaps[id] = map;
  }

  const fontMaps = {};
  for (const [id, body] of Object.entries(objs)) {
    const m = body.match(/\/ToUnicode\s+(\d+)\s+0\s+R/);
    if (m) fontMaps[id] = cmaps[m[1]] || {};
  }

  let allText = "";
  for (const body of Object.values(objs)) {
    if (!/\/Type\s*\/Page\b|\/Type\/Page\b/.test(body) || /\/Type\s*\/Pages\b/.test(body)) continue;

    const pageFontMaps = {};
    let resourceText = body;
    const resourceRef = body.match(/\/Resources\s+(\d+)\s+0\s+R/);
    if (resourceRef && objs[resourceRef[1]]) resourceText += "\n" + objs[resourceRef[1]];
    const fontRef = resourceText.match(/\/Font\s+(\d+)\s+0\s+R/);
    if (fontRef && objs[fontRef[1]]) resourceText += "\n" + objs[fontRef[1]];

    for (const m of resourceText.matchAll(/\/(F\d+)\s+(\d+)\s+0\s+R/g)) {
      if (fontMaps[m[2]]) pageFontMaps[m[1]] = fontMaps[m[2]];
    }
    const fallback = Object.values(pageFontMaps)[0] || {};
    const contentIds = [...body.matchAll(/\/Contents\s+(\d+)\s+0\s+R/g)].map((m) => m[1]);
    let pageText = "";

    for (const contentId of contentIds) {
      const stream = inflateObjectStream(objs, contentId);
      let currentFont = null;
      const tokenRe = /\/(F\d+)\s+\d+(?:\.\d+)?\s+Tf|<([0-9A-F]+)>\s*Tj|\[((?:.|\n)*?)\]\s*TJ/g;
      for (const token of stream.matchAll(tokenRe)) {
        if (token[1]) {
          currentFont = token[1];
          continue;
        }
        const map = pageFontMaps[currentFont] || fallback;
        const hexes = token[2] ? [token[2]] : [...token[3].matchAll(/<([0-9A-F]+)>/g)].map((m) => m[1]);
        for (const hex of hexes) {
          for (let i = 0; i < hex.length; i += 2) {
            pageText += map[hex.slice(i, i + 2).toUpperCase()] || "";
          }
          pageText += " ";
        }
      }
    }
    allText += pageText.replace(/\s+/g, " ").trim() + "\n---PAGE---\n";
  }
  return allText;
}

console.log(decodePdf(process.argv[2]));
