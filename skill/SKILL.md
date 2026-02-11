---
name: catime
description: "Browse and display AI-generated hourly cat images from the catime project. Every hour, a unique cat is born with AI art. Use when user wants to see cat images, browse the cat gallery, or get the latest AI-generated cat."
metadata:
  openclaw:
    requires:
      bins: [uv]
    install:
      - id: catime-pip
        kind: pip
        package: catime
        bins: [catime]
        label: "Install catime (pip)"
---

# catime - AI-Generated Hourly Cat Images 🐱

Every hour, catime generates a unique AI cat image. This skill lets you browse and display them.

## Usage

### View latest cat
```bash
catime latest
```

### View specific cat by number
```bash
catime 42
```

### View today's cats
```bash
catime today
```

### View cats from a specific date
```bash
catime 2026-01-30
```

### List all cats
```bash
catime --list
```

### Open gallery in browser
```bash
catime view
```

## What is catime?
- 🎨 AI-generated cat images every hour using Google Gemini
- 📚 103+ art styles in the style library
- 🐱 Each cat has a unique story and personality
- 🌐 Gallery: https://yazelin.github.io/catime/
- 📦 PyPI: `pip install catime`
- ⭐ GitHub: https://github.com/yazelin/catime
