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

app.post('/init', async (req, res) => {
  const { name, with_graph, with_ai, with_db, with_auth, with_jobs } = req.body;
  if (!name) return res.status(400).json({ error: 'Missing name' });
  const tmpDir = fs.mkdtempSync(path.join(os.tmpdir(), 'ferrum-'));
  const projectDir = path.join(tmpDir, name);
  const args = [
    'cargo run --quiet -- init',
    projectDir,
    with_graph ? '--with-graph' : '',
    with_ai ? '--with-ai' : '',
    with_db ? '--with-db' : '',
    with_auth ? '--with-auth' : '',
    with_jobs ? '--with-jobs' : '',
  ]
    .filter(Boolean)
    .join(' ');
  try {
    await runCommand(args, path.resolve(__dirname, '..'));
    res.setHeader('Content-Type', 'application/zip');
    res.setHeader('Content-Disposition', `attachment; filename=${name}.zip`);
    const archive = archiver('zip');
    archive.directory(projectDir, false);
    archive.finalize();
    archive.pipe(res);
  } catch (err) {
    res.status(500).json({ error: String(err) });
  }
});

app.post('/dev', async (req, res) => {
  const { with_graph, with_ai } = req.body || {};
  const services = ['backend', 'frontend', 'db'];
  if (with_graph) services.push('graphdb');
  if (with_ai) services.push('llm');
  const cmd = `docker-compose up -d ${services.join(' ')}`;
  try {
    const out = await runCommand(cmd, path.resolve(__dirname, '..'));
    res.json({ output: out });
  } catch (err) {
    res.status(500).json({ error: String(err) });
  }
});

app.post('/sync', async (req, res) => {
  const { yaml, uri, user, password } = req.body;
  if (!yaml) return res.status(400).json({ error: 'Missing yaml' });
  const tmpDir = fs.mkdtempSync(path.join(os.tmpdir(), 'ferrum-'));
  const yamlPath = path.join(tmpDir, 'grafo.yaml');
  fs.writeFileSync(yamlPath, yaml);
  const args = [
    'cargo run --quiet -- sync',
    yamlPath,
    `--uri ${uri || 'bolt://localhost:7687'}`,
    `--user ${user || 'neo4j'}`,
    `--password ${password || 'test'}`,
  ].join(' ');
  try {
    const out = await runCommand(args, path.resolve(__dirname, '..'));
    res.json({ output: out });
  } catch (err) {
    res.status(500).json({ error: String(err) });
  }
});

app.post('/save', async (req, res) => {
  const { yaml } = req.body || {};
  if (!yaml) return res.status(400).json({ error: 'Missing yaml' });
  const filePath = path.resolve(__dirname, 'grafo.yaml');
  try {
    fs.writeFileSync(filePath, yaml);
    const cmd = `cargo run --quiet -- compile ${filePath}`;
    await runCommand(cmd, path.resolve(__dirname, '..'));
    res.json({ ok: true });
  } catch (err) {
    res.status(500).json({ error: String(err) });
  }
});

app.post('/migrate', async (_req, res) => {
  try {
    const out = await runCommand(
      'cargo run --quiet -- migrate',
      path.resolve(__dirname, '..')
    );
    res.json({ output: out });
  } catch (err) {
    res.status(500).json({ error: String(err) });
  }
});

const PORT = process.env.PORT || 3001;
app.listen(PORT, () => {
  console.log(`CLI server running on port ${PORT}`);
});

