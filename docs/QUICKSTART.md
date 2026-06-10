# CineForge Quickstart

## Install

```bash
# Clone or extract the release archive
git clone https://github.com/lumenhelixsolutions/cineFORGE.git
cd cineforge

# Install Python dependencies
pip install -e ".[vertex,fal,dev]"

# Install UI dependencies
cd ui && npm install && cd ..

# Install Tauri CLI (requires Rust)
cargo install tauri-cli
```

## First Project

1. **Start the backend**
   ```bash
   python -m backend.app
   ```

2. **Open the UI**
   ```bash
   cd ui && npm run dev
   ```
   Or launch the Tauri desktop app:
   ```bash
   cargo tauri dev
   ```

3. **Create a project** via the UI or API:
   ```bash
   curl -X POST http://127.0.0.1:8765/projects \
     -H "Content-Type: application/json" \
     -d '{"name":"My First Video","aspect_ratio":"16:9","target_duration_sec":60}'
   ```

4. **Upload a source document**
   ```bash
   curl -X POST http://127.0.0.1:8765/projects/{id}/sources \
     -F "file=@story.txt"
   ```

5. **Generate treatment & storyboard**
   ```bash
   curl -X POST http://127.0.0.1:8765/projects/{id}/treatment
   curl -X POST http://127.0.0.1:8765/projects/{id}/storyboard
   ```

## Render

Render all draft shots:
```bash
curl -X POST http://127.0.0.1:8765/projects/{id}/render \
  -H "Content-Type: application/json" \
  -d '{"shot_ids":null}'
```

Poll the project endpoint until all shots are `done`.

## Stitch

Assemble the final video:
```bash
curl -X POST http://127.0.0.1:8765/projects/{id}/stitch \
  -H "Content-Type: application/json" \
  -d '{"output_name":"master"}'
```

The output MP4 and timeline sidecar JSON will be in the project directory.

## Next Steps

- Configure routing profiles: see `STACK_BUILDER.md`
- Run diagnostics: `GET /diagnostics`
- Export a project bundle: `POST /projects/{id}/export-bundle`
