const $ = id => document.getElementById(id);
let imageId = null, flipH = false, flipV = false, rotate = 0, timer = null, currentBlobUrl = null;

const sliders = ["brightness","contrast","saturation","sharpness","blur","scale"];
const defaults = {brightness:100,contrast:100,saturation:100,sharpness:100,blur:0,scale:100};

function params() {
  const p = {
    auto_enhance: $("auto_enhance").checked,
    remove_bg: $("remove_bg").checked,
    filter: $("filter").value,
    rotate, flip_h: flipH, flip_v: flipV,
  };
  sliders.forEach(s => p[s] = Number($(s).value));
  const crop = {x:+$("cx").value, y:+$("cy").value, w:+$("cw").value, h:+$("ch").value};
  if (crop.x || crop.y || crop.w !== 100 || crop.h !== 100) p.crop = crop;
  return p;
}

async function render(format = "png", forDownload = false) {
  if (!imageId) return;
  if (!forDownload) $("busy").hidden = false;
  const res = await fetch("/api/process", {
    method: "POST", headers: {"Content-Type": "application/json"},
    body: JSON.stringify({id: imageId, params: params(), format}),
  });
  $("busy").hidden = true;
  if (!res.ok) { alert("Processing failed"); return null; }
  const blob = await res.blob();
  if (forDownload) return blob;
  if (currentBlobUrl) URL.revokeObjectURL(currentBlobUrl);
  currentBlobUrl = URL.createObjectURL(blob);
  $("preview").src = currentBlobUrl;
}

function schedule() { clearTimeout(timer); timer = setTimeout(() => render(), 200); }

async function upload(file) {
  if (!file || !file.type.startsWith("image/")) return alert("Please choose an image file.");
  const fd = new FormData(); fd.append("image", file);
  const res = await fetch("/api/upload", {method: "POST", body: fd});
  const data = await res.json();
  if (!res.ok) return alert(data.error || "Upload failed");
  imageId = data.id;
  $("drop").hidden = true; $("preview").hidden = false;
  $("reset").disabled = $("download").disabled = false;
  resetControls(); render();
}

function resetControls() {
  sliders.forEach(s => $(s).value = defaults[s]);
  $("auto_enhance").checked = $("remove_bg").checked = false;
  $("filter").value = "none";
  ["cx","cy"].forEach(i => $(i).value = 0); ["cw","ch"].forEach(i => $(i).value = 100);
  flipH = flipV = false; rotate = 0;
}

$("open").onclick = $("drop").onclick = () => $("file").click();
$("file").onchange = e => upload(e.target.files[0]);
$("reset").onclick = () => { resetControls(); render(); };
["dragover","dragenter"].forEach(ev => $("stage").addEventListener(ev, e => { e.preventDefault(); $("drop").classList.add("over"); }));
["dragleave","drop"].forEach(ev => $("stage").addEventListener(ev, e => { e.preventDefault(); $("drop").classList.remove("over"); }));
$("stage").addEventListener("drop", e => upload(e.dataTransfer.files[0]));

sliders.concat(["filter","cx","cy","cw","ch"]).forEach(id => $(id).addEventListener("input", schedule));
["auto_enhance","remove_bg"].forEach(id => $(id).addEventListener("change", schedule));
$("rotL").onclick = () => { rotate = (rotate + 270) % 360; schedule(); };
$("rotR").onclick = () => { rotate = (rotate + 90) % 360; schedule(); };
$("flipH").onclick = () => { flipH = !flipH; schedule(); };
$("flipV").onclick = () => { flipV = !flipV; schedule(); };

$("download").onclick = async () => {
  const fmt = $("format").value;
  const blob = await render(fmt, true);
  if (!blob) return;
  const a = document.createElement("a");
  a.href = URL.createObjectURL(blob);
  a.download = `edited.${fmt === "jpeg" ? "jpg" : "png"}`;
  a.click();
};
