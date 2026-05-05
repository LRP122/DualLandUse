# Running AgriPV with Docker

This document explains how to run the AgriPV project using Docker. Docker packages the entire application (Python, dependencies, system libraries) into a container so you don't need to install anything locally.

## Prerequisites

You need to have Docker and Docker Compose installed:

- **Docker Desktop** (includes both Docker and Docker Compose)
  - Mac: https://docs.docker.com/desktop/install/mac-install/
  - Windows: https://docs.docker.com/desktop/install/windows-install/
  - Linux: https://docs.docker.com/engine/install/

After installing, verify they work:
```bash
docker --version
docker-compose --version
```

## Quick Start (Easiest Way)

### First Time Setup

```bash
cd /path/to/AgripholtiacsProject
docker-compose build
docker-compose up
```

Then open your browser to: **http://localhost:8080**

### Next Time

Just run:
```bash
docker-compose up
```

Stop the app with: **Ctrl+C**

---

## How It Works

### For Others (Anyone Running This)

If someone else wants to run your project, they just need:
1. Docker Desktop installed
2. Run: `docker-compose up`
3. Open http://localhost:8080

No need to install Python, libraries, GDAL, PROJ, or anything else!

### For You (Development)

You can edit files on your computer and the changes automatically appear in the running app:

```bash
# Start the app
docker-compose up

# In your editor, edit src/scenario_calculations.py or any file
# Save the file
# The app automatically reloads with your changes
# Refresh browser to see result

# Stop when done
# Press Ctrl+C
```

This is because your project folder is **mounted as a volume** inside the container. Changes sync automatically.

---

## Useful Commands

### View Logs
```bash
docker-compose logs -f
```
(-f means "follow" - shows new logs in real-time)

### Stop the App
```bash
docker-compose down
```

### Rebuild (if you change requirements.txt)
```bash
docker-compose build
docker-compose up
```

### Remove Everything (clean up)
```bash
docker-compose down -v
```

### Run a Command Inside Container
```bash
docker-compose exec AgriPV python -c "import src.scenario_calculations; print(src.scenario_calculations.CROP_PARAMS)"
```

---

## How It's Set Up

### `Dockerfile`
- Defines the image: Python 3.12 + system dependencies (GDAL, PROJ, etc.)
- Installs all Python requirements
- Runs `python app/app.py` when container starts

### `docker-compose.yml`
- Orchestrates the container
- Maps port 8080 (container) → 8080 (your computer)
- Mounts your project folder inside the container
- Sets environment for live reloading

### `.dockerignore`
- Excludes unnecessary files (.venv, __pycache__, etc.)
- Makes the image smaller and builds faster

---

## Troubleshooting

### "Port 8080 is already in use"
Another app is using port 8080. Either:
1. Stop the other app
2. Or, change the port in `docker-compose.yml`:
   ```yaml
   ports:
     - "8081:8080"  # Now use http://localhost:8081
   ```

### "Cannot connect to Docker daemon"
Docker Desktop isn't running. Start it from your Applications folder.

### "ModuleNotFoundError" or missing libraries
Rebuild the image:
```bash
docker-compose build --no-cache
docker-compose up
```

### App doesn't reload when I edit files
This is expected for some systems. Restart the app:
```bash
# Stop: Ctrl+C
docker-compose up
```

### Changes don't appear in browser
Clear browser cache (Ctrl+Shift+Delete) or use private/incognito window.

---

## Development Tips

### Edit Python Files

All your Python files are directly mounted:
```
Your Computer          Container
src/scenario_calculations.py ◄──► /app/src/scenario_calculations.py
app/app.py ◄──► /app/app.py
```

Edit on your computer, changes appear in container immediately.

### Add New Dependencies

1. Add to `requirements.txt`
2. Stop the container: Ctrl+C
3. Rebuild: `docker-compose build`
4. Restart: `docker-compose up`

### Access the Bash Shell

To debug or run commands inside the container:
```bash
docker-compose exec AgriPV bash
```

Then you're inside the container:
```bash
# You can now run Python commands
python -c "from src.scenario_calculations import CROP_PARAMS; print(CROP_PARAMS)"

# Or check files
ls -la /app/src/

# Exit with: exit
```

---

## When NOT to Use Docker

- If you're only working locally and want maximum simplicity: stick with `./run.sh`
- If you want to modify the infrastructure itself (though you shouldn't need to)

## When TO Use Docker

- ✅ Sharing the project with others
- ✅ Setting up on a new computer
- ✅ Running on Linux servers
- ✅ Making sure it works the same everywhere
- ✅ Avoiding dependency conflicts

---

## Need Help?

See official docs:
- Docker: https://docs.docker.com/
- Docker Compose: https://docs.docker.com/compose/
