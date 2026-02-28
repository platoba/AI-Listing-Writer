# Changelog

## [5.0.0] - 2026-03-01

### Added
- **Marketplace Trends Analyzer** (`app/marketplace_trends.py`)
  - SQLite-backed trend data storage with bulk ingestion
  - Keyword velocity scoring and direction detection (rising/breakout/declining/stable/new)
  - Seasonal pattern recognition (Q4 holiday, summer, Valentine's, etc.)
  - Niche opportunity discovery with scoring and status classification
  - Cross-platform keyword analysis with arbitrage detection
  - Comprehensive trend reports with text formatting
  - Related keyword tracking and relationship mapping
- **Listing Health Monitor** (`app/listing_health.py`)
  - 8-category health checks: title, description, SEO, images, pricing, compliance, content quality, completeness
  - Platform-specific validation rules for 8 marketplaces
  - A+ to F grading system with score change tracking
  - Automated alert system: score drops, missing fields, compliance violations
  - Monitored listing database with scheduled health checks
  - Batch checking with summary reports and dashboard stats
  - Prohibited word detection and keyword density analysis
- **Cross-Platform Migration** (`app/migration.py`)
  - Support for 10 platforms: Amazon, Shopee, Lazada, AliExpress, eBay, Walmart, Etsy, Temu, TikTok Shop, Mercado Libre
  - Compatibility analysis with scoring before migration
  - Auto-fix: HTML stripping, title truncation, bullet point generation/merging, image trimming
  - Category mapping between major platform pairs
  - Batch migration with common issue aggregation
  - Platform comparison tool
- `pyproject.toml` for modern Python packaging
- 3 new test files with comprehensive coverage

### Stats
- Tests: 711 → 900+ (190+ new tests)
- New modules: 3 (`marketplace_trends`, `listing_health`, `migration`)
- New code: ~2,500 lines

## [4.0.0] - 2026-02-28

### Added
- Review Analyzer (`app/review_analyzer.py`)
- Seasonal Optimizer (`app/seasonal.py`)
- Image Optimizer (`app/image_optimizer.py`)
- 15 new test files

## [3.0.0] - 2026-02-27

### Added
- Keyword research module
- Export system (CSV/JSON/TXT/HTML)
- Compare mode
- 50 tests

## [2.0.0] - 2026-02-27

### Added
- Modular architecture refactoring
- Batch mode processing
- Optimize and translate commands
- eBay and Walmart platform support
- Redis history storage
- Docker Compose + CI/CD
- 22 tests

## [1.0.0] - 2026-02-27

### Added
- Initial release
- 6 platform listing generator (Amazon, Shopee, Lazada, AliExpress, eBay, Walmart)
- Telegram Bot interface
- OpenAI integration
