const express = require('express');
const { exec } = require('child_process');
const fs = require('fs');
const path = require('path');
const os = require('os');
const archiver = require('archiver');

const app = express();
app.use(express.json({ limit: '10mb' }));

function runCommand(cmd, cwd) {
  return new Promise((resolve, reject) => {
    exec(cmd, { cwd }, (err, stdout, stderr) => {
      if (err) {
        reject(stderr || err.message);
      } else {
        resolve(stdout);
      }
    });
  });
}

app.post('/compile', async (req, res) => {
  const { yaml } = req.body;
  if (!yaml) return res.status(400).json({ error: 'Missing yaml' });
  try {
    const tmpDir = fs.mkdtempSync(path.join(os.tmpdir(), 'ferrum-'));
    const yamlPath = path.join(tmpDir, 'grafo.yaml');
    fs.writeFileSync(yamlPath, yaml);
    const outDir = path.join(tmpDir, 'out');
    const cmd = `cargo run --quiet -- compile ${yamlPath} --output ${outDir}`;
    await runCommand(cmd, path.resolve(__dirname, '..'));
    res.setHeader('Content-Type', 'application/zip');
    res.setHeader('Content-Disposition', 'attachment; filename=output.zip');
    const archive = archiver('zip');
    archive.directory(outDir, false);
    archive.finalize();
    archive.pipe(res);
  } catch (err) {
    res.status(500).json({ error: String(err) });
  }
});

app.post('/prompt', async (req, res) => {
  const { text } = req.body;
  if (!text) return res.status(400).json({ error: 'Missing text' });
  try {
    const tmpDir = fs.mkdtempSync(path.join(os.tmpdir(), 'ferrum-'));
    const outPath = path.join(tmpDir, 'generated.yaml');
    const cmd = `cargo run --quiet -- prompt "${text}" --output ${outPath}`;
    await runCommand(cmd, path.resolve(__dirname, '..'));
    const yaml = fs.readFileSync(outPath, 'utf8');
    res.json({ yaml });
  } catch (err) {
    res.status(500).json({ error: String(err) });
  }
});

const PORT = process.env.PORT || 3001;
app.listen(PORT, () => {
  console.log(`CLI server running on port ${PORT}`);
});

