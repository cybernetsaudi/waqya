# Waqya Categories — Frontend / Menu Guide

**Source of truth:** `automation/waqya_categories.yaml`  
**JSON export (for theme):** `wordpress/theme/waqya/config/categories.json`

Regenerate JSON after taxonomy edits:

```bash
cd automation && python export_categories.py
```

## Design rules (do not break)

1. **One primary category per post** — drives archive URL and breadcrumb.
2. **Menu uses `menu` groups** — never dump all 35 categories in one flat list.
3. **Regions/topics** are also **tags** on posts — use for filters, not top-level nav (unless a “Regions” mega-menu).
4. **Hero sliders** — homepage and every `/category/{slug}/` archive show the 5 most recent posts in a slider (not a single oversized lead image). Slider post IDs are excluded from the archive grid on page 1.

## Theme implementation

| Piece | Location |
|-------|----------|
| JSON loader | `inc/taxonomy-config.php` |
| Grouped nav | `template-parts/nav/menu-groups.php` |
| Post slider | `template-parts/slider/`, `inc/slider.php`, `assets/css/slider.css` |
| Homepage sections | One card grid per menu group (News Desk, Regions, Topics) |

## Menu structure (3 groups)

| Group | Purpose | Example items |
|-------|---------|----------------|
| News Desk | Breaking / topical desks | War & Conflict, Immigration, Politics |
| Regions | Geographic desks | Middle East, South Asia, UK, US |
| Topics | Thematic desks | Religion, Tech & AI, Health |

## All primary categories (35)

See `categories.json` → `primary_categories` for labels, slugs, descriptions, and `menu_group`.

## Auto-publish

Pipeline setting `pipeline.auto_publish: true` in `config.yaml` — new posts go **live** without manual approval. Set to `false` for draft review workflow.
