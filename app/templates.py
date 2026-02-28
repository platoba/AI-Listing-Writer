"""Category-specific listing templates with industry best practices.

Provides pre-built listing structures, power words, and platform-specific
optimizations for 12 product categories across all 8 supported platforms.
"""
from dataclasses import dataclass, field
from typing import Optional
from enum import Enum


class Category(str, Enum):
    ELECTRONICS = "electronics"
    FASHION = "fashion"
    HOME_GARDEN = "home_garden"
    BEAUTY = "beauty"
    SPORTS = "sports"
    TOYS = "toys"
    FOOD = "food"
    AUTOMOTIVE = "automotive"
    PET = "pet"
    OFFICE = "office"
    BABY = "baby"
    HEALTH = "health"


@dataclass
class PowerWords:
    """Category-specific persuasion vocabulary."""
    urgency: list[str] = field(default_factory=list)
    trust: list[str] = field(default_factory=list)
    value: list[str] = field(default_factory=list)
    emotion: list[str] = field(default_factory=list)
    technical: list[str] = field(default_factory=list)


@dataclass
class CategoryTemplate:
    """Full template for a product category."""
    category: Category
    name: str
    description: str
    power_words: PowerWords
    title_patterns: list[str]
    bullet_patterns: list[str]
    description_structure: list[str]
    seo_keywords_hints: list[str]
    avoid_words: list[str]
    platform_tips: dict[str, list[str]] = field(default_factory=dict)
    emoji_palette: list[str] = field(default_factory=list)
    typical_features: list[str] = field(default_factory=list)
    target_audiences: list[str] = field(default_factory=list)


# =============================================================================
# Power word libraries per category
# =============================================================================

_ELECTRONICS_WORDS = PowerWords(
    urgency=["limited stock", "newest model", "just released", "while supplies last",
             "flash deal", "exclusive launch", "pre-order now"],
    trust=["certified", "warranty", "genuine", "authorized dealer", "FCC approved",
           "CE certified", "tested", "verified", "factory sealed"],
    value=["bundle deal", "all-in-one", "premium", "professional-grade", "best-in-class",
           "flagship", "next-generation", "ultra", "pro"],
    emotion=["game-changer", "breakthrough", "revolutionary", "cutting-edge",
             "must-have", "life-changing", "incredible", "stunning"],
    technical=["5GHz", "USB-C", "Bluetooth 5.3", "Wi-Fi 6E", "4K UHD", "HDR10+",
               "fast charging", "low latency", "noise cancelling", "AI-powered"],
)

_FASHION_WORDS = PowerWords(
    urgency=["trending now", "selling fast", "limited edition", "seasonal must-have",
             "this season's hottest", "back in stock"],
    trust=["authentic", "handcrafted", "genuine leather", "ethically sourced",
           "sustainable", "quality assured", "premium fabric"],
    value=["versatile", "timeless", "wardrobe essential", "everyday luxury",
           "classic", "effortless style", "dress up or down"],
    emotion=["elegant", "stunning", "gorgeous", "chic", "flattering", "confidence-boosting",
             "head-turning", "show-stopping", "Instagram-worthy"],
    technical=["breathable", "moisture-wicking", "wrinkle-free", "stretch fabric",
               "reinforced stitching", "fade-resistant", "machine washable"],
)

_HOME_GARDEN_WORDS = PowerWords(
    urgency=["seasonal sale", "spring collection", "holiday must-have",
             "limited batch", "artisan made"],
    trust=["BPA-free", "food-safe", "non-toxic", "eco-friendly", "USDA organic",
           "lab-tested", "child-safe", "pet-safe"],
    value=["space-saving", "multi-functional", "easy-to-clean", "durable",
           "long-lasting", "investment piece", "heirloom quality"],
    emotion=["cozy", "inviting", "transform your space", "home sweet home",
             "sanctuary", "dream home", "Pinterest-worthy"],
    technical=["stainless steel", "solid wood", "tempered glass", "UV-resistant",
               "weatherproof", "energy-efficient", "smart home compatible"],
)

_BEAUTY_WORDS = PowerWords(
    urgency=["cult favorite", "viral sensation", "TikTok famous", "award-winning",
             "sold out 3x", "celebrity-approved"],
    trust=["dermatologist-tested", "clinically proven", "cruelty-free", "vegan",
           "hypoallergenic", "paraben-free", "sulfate-free", "fragrance-free"],
    value=["salon-quality", "professional results", "luxury formula", "concentrated",
           "multi-use", "travel-friendly", "long-lasting"],
    emotion=["radiant", "flawless", "glow", "youthful", "luminous", "silky smooth",
             "effortless beauty", "self-care essential"],
    technical=["SPF 50+", "retinol", "hyaluronic acid", "vitamin C", "niacinamide",
               "peptides", "ceramides", "AHA/BHA"],
)

_SPORTS_WORDS = PowerWords(
    urgency=["competition-ready", "new season gear", "limited colorway",
             "athlete-approved", "championship edition"],
    trust=["ISO certified", "competition-grade", "professional athletes use",
           "tested in extreme conditions", "endorsed by", "safety certified"],
    value=["performance-driven", "elite", "competition-level", "versatile training",
           "all-weather", "multi-sport", "portable"],
    emotion=["unleash your potential", "push your limits", "dominate", "unstoppable",
             "beast mode", "personal best", "champion mindset"],
    technical=["carbon fiber", "shock-absorbing", "anti-slip", "quick-dry",
               "compression fit", "ergonomic design", "lightweight alloy"],
)

_TOYS_WORDS = PowerWords(
    urgency=["holiday bestseller", "gift-ready", "trending toy", "award-winning toy",
             "flying off shelves"],
    trust=["ASTM certified", "CPSIA compliant", "age-appropriate", "non-toxic paint",
           "lead-free", "small parts tested", "parent-approved"],
    value=["educational", "STEM learning", "hours of fun", "screen-free play",
           "grows with your child", "family bonding"],
    emotion=["magical", "imagination spark", "adventure awaits", "pure joy",
             "unforgettable gift", "childhood wonder", "creative freedom"],
    technical=["BPA-free plastic", "rounded edges", "rechargeable battery",
               "app-compatible", "modular design", "easy assembly"],
)

_FOOD_WORDS = PowerWords(
    urgency=["fresh batch", "seasonal harvest", "limited roast", "small batch",
             "artisanal", "just arrived"],
    trust=["USDA organic", "non-GMO", "gluten-free", "kosher", "halal",
           "FDA approved", "third-party tested", "farm-to-table"],
    value=["family-size", "bulk savings", "pantry staple", "meal-prep friendly",
           "subscription & save", "value pack"],
    emotion=["delicious", "mouthwatering", "irresistible", "comfort food",
             "home-cooked taste", "foodie-approved", "taste of tradition"],
    technical=["cold-pressed", "slow-roasted", "stone-ground", "freeze-dried",
               "vacuum-sealed", "no preservatives", "zero sugar"],
)

_AUTOMOTIVE_WORDS = PowerWords(
    urgency=["last chance", "closeout special", "model year clearance",
             "limited production"],
    trust=["OEM quality", "ISO 9001", "SAE certified", "direct fit replacement",
           "lifetime warranty", "factory specs"],
    value=["universal fit", "easy install", "plug-and-play", "bolt-on upgrade",
           "professional grade", "daily driver ready"],
    emotion=["unleash horsepower", "head-turner", "street presence", "adrenaline rush",
             "drive with confidence"],
    technical=["CNC machined", "heat-treated", "corrosion-resistant", "torque rating",
               "load capacity", "vibration dampened"],
)

_PET_WORDS = PowerWords(
    urgency=["vet-recommended", "new formula", "bestseller", "limited flavor"],
    trust=["vet-approved", "AAFCO compliant", "human-grade", "allergen-free",
           "no artificial colors", "third-party tested"],
    value=["long-lasting", "easy to clean", "indestructible", "multi-pet household",
           "all breeds", "all life stages"],
    emotion=["tail-wagging", "purr-fect", "happy pet = happy life", "fur baby approved",
             "unconditional love", "pet parent tested"],
    technical=["orthopedic memory foam", "chew-resistant", "waterproof liner",
               "dental health formula", "joint support", "probiotic blend"],
)

_OFFICE_WORDS = PowerWords(
    urgency=["back to school", "new semester", "tax season essential",
             "work-from-home upgrade"],
    trust=["ISO certified", "ENERGY STAR", "enterprise-grade", "industry standard",
           "GDPR compliant"],
    value=["boost productivity", "time-saving", "cost-effective", "all-in-one solution",
           "scalable", "team-friendly"],
    emotion=["work smarter", "level up your desk", "professional impression",
             "organized life", "stress-free"],
    technical=["wireless", "cloud-compatible", "cross-platform", "encrypted",
               "high-speed", "ergonomic certified"],
)

_BABY_WORDS = PowerWords(
    urgency=["registry must-have", "newborn essential", "nursery bestseller",
             "award-winning baby product"],
    trust=["pediatrician-recommended", "CPSC compliant", "JPMA certified",
           "hospital-grade", "organic cotton", "chemical-free"],
    value=["grows with baby", "convertible", "multi-stage", "value bundle",
           "shower gift set", "complete kit"],
    emotion=["gentle care", "sweet dreams", "precious moments", "peace of mind",
             "bonding time", "safe & snug"],
    technical=["anti-colic", "temperature-sensitive", "hypoallergenic fabric",
               "breathable mesh", "5-point harness", "one-hand operation"],
)

_HEALTH_WORDS = PowerWords(
    urgency=["new formula", "clinically studied", "breakthrough supplement",
             "limited supply", "doctor-recommended"],
    trust=["GMP certified", "third-party tested", "FDA registered facility",
           "USP verified", "NSF certified", "cGMP compliant"],
    value=["90-day supply", "subscription savings", "complete formula",
           "all-in-one daily", "family health pack"],
    emotion=["feel your best", "natural wellness", "vitality boost", "energy & focus",
             "immune warrior", "holistic health"],
    technical=["bioavailable", "time-release", "enteric-coated", "standardized extract",
               "chelated minerals", "liposomal delivery"],
)


# =============================================================================
# Full category templates
# =============================================================================

CATEGORY_TEMPLATES: dict[Category, CategoryTemplate] = {
    Category.ELECTRONICS: CategoryTemplate(
        category=Category.ELECTRONICS,
        name="Electronics & Tech",
        description="Smartphones, laptops, accessories, smart home devices, audio equipment",
        power_words=_ELECTRONICS_WORDS,
        title_patterns=[
            "[Brand] [Product] [Key Spec] - [Benefit] | [Compatibility]",
            "[Product] [Model] with [Feature] - [Spec] [Use Case]",
            "[Adjective] [Product] [Spec] for [Audience] - [Feature1] & [Feature2]",
        ],
        bullet_patterns=[
            "⚡ [FEATURE] — [Technical spec] that delivers [benefit]",
            "🔋 [BATTERY/POWER] — [Duration] hours of [use case] on a single charge",
            "🎯 [PRECISION] — [Technical detail] for [professional/casual] use",
            "📦 [PACKAGE] — Includes [accessory1], [accessory2], and [warranty]",
            "💡 [SMART FEATURE] — [AI/Auto feature] that [saves time/improves experience]",
        ],
        description_structure=[
            "Opening hook (problem solved)",
            "Key specifications table",
            "Use case scenarios (3-4)",
            "Compatibility information",
            "What's in the box",
            "Warranty & support info",
        ],
        seo_keywords_hints=["model number", "compatibility terms", "vs competitor", "year model",
                            "use case keywords", "problem keywords"],
        avoid_words=["cheap", "knockoff", "copy", "clone", "fake"],
        platform_tips={
            "amazon": ["Include model number in title", "Backend keywords: competitor names",
                       "Use A+ Content for comparison tables"],
            "shopee": ["Add 🔥 emoji for specs", "Include voucher mention",
                       "Video demo reference"],
            "aliexpress": ["Emphasize shipping speed", "Include voltage compatibility",
                          "Multi-country plug mention"],
        },
        emoji_palette=["⚡", "🔋", "📱", "💻", "🎧", "🖥️", "⌨️", "🎮", "📡", "🔌"],
        typical_features=["battery life", "connectivity", "display", "processor",
                         "storage", "camera", "audio", "build quality"],
        target_audiences=["tech enthusiasts", "professionals", "students", "gamers",
                         "remote workers", "content creators"],
    ),

    Category.FASHION: CategoryTemplate(
        category=Category.FASHION,
        name="Fashion & Apparel",
        description="Clothing, shoes, accessories, jewelry, bags",
        power_words=_FASHION_WORDS,
        title_patterns=[
            "[Brand] [Product] for [Gender] - [Style] [Material] [Occasion]",
            "[Adjective] [Product] [Style] - [Size Range] | [Season] Collection",
            "[Product] [Feature] [Material] - [Occasion] [Benefit]",
        ],
        bullet_patterns=[
            "👗 [STYLE] — [Aesthetic description] perfect for [occasion]",
            "✨ [MATERIAL] — [Fabric type] that's [comfort benefit] all day",
            "📏 [FIT] — [Fit type] with [sizing detail] - see size chart",
            "🧵 [QUALITY] — [Construction detail] for [durability claim]",
            "🎁 [VERSATILE] — Style it [way1] for [occasion1] or [way2] for [occasion2]",
        ],
        description_structure=[
            "Style story / mood setting",
            "Material & construction details",
            "Fit guide with measurements",
            "Styling suggestions (3 looks)",
            "Care instructions",
            "Size chart reference",
        ],
        seo_keywords_hints=["occasion", "season", "color name", "body type", "style name",
                            "material type", "size keywords"],
        avoid_words=["one size fits all (unless true)", "slimming (sensitive)", "sexy (some platforms)"],
        platform_tips={
            "amazon": ["Include size chart in images", "Use brand story module",
                       "Mention return policy"],
            "shopee": ["Heavy emoji use", "Include model measurements",
                       "Reference trending styles"],
            "tiktok_shop": ["Link to styling video", "Use trending hashtags",
                           "Mention influencer reviews"],
        },
        emoji_palette=["👗", "👔", "👠", "👜", "💎", "✨", "🧣", "👒", "🕶️", "💅"],
        typical_features=["material", "fit type", "size range", "care instructions",
                         "color options", "occasion suitability"],
        target_audiences=["fashion-forward women", "professional men", "teens",
                         "plus-size", "maternity", "athleisure enthusiasts"],
    ),

    Category.HOME_GARDEN: CategoryTemplate(
        category=Category.HOME_GARDEN,
        name="Home & Garden",
        description="Furniture, decor, kitchen, garden tools, bedding, storage",
        power_words=_HOME_GARDEN_WORDS,
        title_patterns=[
            "[Brand] [Product] [Size/Dimension] - [Material] [Style] for [Room]",
            "[Adjective] [Product] Set of [N] - [Feature] | [Material]",
            "[Product] [Color] [Material] - [Room/Use] [Benefit]",
        ],
        bullet_patterns=[
            "🏠 [DESIGN] — [Style] aesthetic that complements [room type] decor",
            "🔨 [DURABILITY] — Made from [material] built to last [duration]",
            "📐 [DIMENSIONS] — [L x W x H] fits perfectly in [space type]",
            "🧹 [EASY CARE] — [Cleaning method] keeps it looking new",
            "📦 [ASSEMBLY] — [Assembly time] setup with [included tools]",
        ],
        description_structure=[
            "Room transformation vision",
            "Dimensions & specifications",
            "Material & finish details",
            "Assembly instructions overview",
            "Care & maintenance guide",
            "Styling suggestions",
        ],
        seo_keywords_hints=["room name", "style (modern/farmhouse/boho)", "dimensions",
                            "material", "color family", "occasion (housewarming)"],
        avoid_words=["flimsy", "temporary", "disposable"],
        emoji_palette=["🏠", "🪴", "🛋️", "🍳", "🌿", "🔨", "💡", "🛏️", "🚿", "🧹"],
        typical_features=["dimensions", "material", "weight capacity", "assembly required",
                         "indoor/outdoor", "color options"],
        target_audiences=["homeowners", "renters", "interior design enthusiasts",
                         "minimalists", "garden lovers", "new homeowners"],
    ),

    Category.BEAUTY: CategoryTemplate(
        category=Category.BEAUTY,
        name="Beauty & Personal Care",
        description="Skincare, makeup, haircare, fragrance, tools",
        power_words=_BEAUTY_WORDS,
        title_patterns=[
            "[Brand] [Product] [Key Ingredient] - [Skin Type] [Benefit] [Size]",
            "[Adjective] [Product] with [Ingredient] - [Result] in [Timeframe]",
            "[Product] [Variant] for [Concern] - [Certification] [Size]",
        ],
        bullet_patterns=[
            "✨ [RESULTS] — [Visible benefit] in as little as [timeframe]",
            "🧪 [FORMULA] — Powered by [key ingredient] at [concentration]",
            "🌿 [CLEAN BEAUTY] — [Certification]: free from [harmful ingredient list]",
            "💆 [TEXTURE] — [Texture description] that [absorption/feel benefit]",
            "🎯 [FOR YOU] — Ideal for [skin type] dealing with [concern]",
        ],
        description_structure=[
            "Before/after transformation story",
            "Key ingredients spotlight",
            "How to use (step-by-step routine)",
            "Skin type compatibility",
            "Clinical results / studies",
            "Full ingredients list",
        ],
        seo_keywords_hints=["skin concern", "ingredient name", "skin type", "routine step",
                            "certification", "vs competitor ingredient"],
        avoid_words=["miracle", "cure", "permanent", "overnight transformation",
                     "anti-aging (regulated in some markets)"],
        emoji_palette=["✨", "🧴", "💄", "💆", "🌿", "🧪", "💋", "🌸", "🧖", "💅"],
        typical_features=["key ingredients", "skin type", "size/volume", "scent",
                         "texture", "certifications"],
        target_audiences=["skincare beginners", "anti-aging seekers", "acne-prone skin",
                         "sensitive skin", "K-beauty fans", "clean beauty advocates"],
    ),

    Category.SPORTS: CategoryTemplate(
        category=Category.SPORTS,
        name="Sports & Outdoors",
        description="Fitness equipment, outdoor gear, sportswear, camping",
        power_words=_SPORTS_WORDS,
        title_patterns=[
            "[Brand] [Product] [Sport] - [Key Spec] [Weight/Size] [Certification]",
            "[Adjective] [Product] for [Activity] - [Material] [Feature]",
            "[Product] [Model] [Color] - [Sport] [Level] [Gender]",
        ],
        bullet_patterns=[
            "🏋️ [PERFORMANCE] — Engineered for [sport/activity] with [tech feature]",
            "💪 [DURABILITY] — [Material] construction withstands [condition]",
            "🎒 [PORTABLE] — Weighs only [weight], folds to [size] for [transport]",
            "🏆 [PRO-LEVEL] — Used by [athlete type] for [competitive advantage]",
            "🛡️ [SAFETY] — [Safety feature] protects against [risk]",
        ],
        description_structure=[
            "Athlete/activity story",
            "Performance specifications",
            "Material & construction",
            "Size/weight guide",
            "Use case scenarios",
            "Safety & warranty info",
        ],
        seo_keywords_hints=["sport name", "skill level", "body measurement",
                            "terrain type", "weather condition", "competition standard"],
        avoid_words=["indestructible (liability)", "guaranteed results"],
        emoji_palette=["🏋️", "🏃", "⚽", "🎯", "🏔️", "🚴", "🏊", "🎿", "🥊", "🏕️"],
        typical_features=["weight", "material", "size options", "weather resistance",
                         "safety certifications", "warranty"],
        target_audiences=["beginners", "intermediate athletes", "professionals",
                         "weekend warriors", "outdoor enthusiasts", "fitness beginners"],
    ),

    Category.TOYS: CategoryTemplate(
        category=Category.TOYS,
        name="Toys & Games",
        description="Children's toys, board games, educational toys, outdoor play",
        power_words=_TOYS_WORDS,
        title_patterns=[
            "[Brand] [Product] for Ages [Range] - [Theme] [Piece Count] [Educational Value]",
            "[Adjective] [Product] [Theme] - [Benefit] Toy for [Age] [Gender]",
            "[Product] Set [Piece Count] - [Category] [Certification] Ages [Range]+",
        ],
        bullet_patterns=[
            "🎮 [FUN FACTOR] — [Play description] that keeps kids engaged for hours",
            "🧠 [LEARNING] — Develops [skill1], [skill2], and [skill3]",
            "👶 [SAFE] — [Certification] certified, [material] with no [harmful substance]",
            "🎁 [GIFT READY] — Beautiful packaging, perfect for [occasion]",
            "👨‍👩‍👧‍👦 [FAMILY] — [Player count] players, ages [range], [play time]",
        ],
        description_structure=[
            "Play scenario description",
            "Educational benefits",
            "Safety certifications",
            "What's included",
            "Age appropriateness details",
            "Gift occasion suggestions",
        ],
        seo_keywords_hints=["age range", "educational type (STEM)", "theme (dinosaur/princess)",
                            "occasion (birthday/Christmas)", "toy category"],
        avoid_words=["cheap", "plastic (negative context)", "battery not included (bury it)"],
        emoji_palette=["🎮", "🧩", "🎨", "🧠", "🎁", "🪀", "🎲", "🤖", "🦕", "🏰"],
        typical_features=["age range", "piece count", "battery requirements",
                         "educational value", "safety certifications", "player count"],
        target_audiences=["parents", "grandparents", "gift givers", "teachers",
                         "homeschooling families"],
    ),

    Category.FOOD: CategoryTemplate(
        category=Category.FOOD,
        name="Food & Grocery",
        description="Snacks, pantry items, supplements, specialty food, beverages",
        power_words=_FOOD_WORDS,
        title_patterns=[
            "[Brand] [Product] [Flavor] - [Certification] [Size] [Pack Count]",
            "[Adjective] [Product] [Variant] - [Diet Type] [Certification] [Size]",
            "[Product] [Origin] [Process] - [Flavor Profile] [Package]",
        ],
        bullet_patterns=[
            "😋 [TASTE] — [Flavor description] made with [quality ingredient]",
            "🌿 [CLEAN] — [Certification]: No [unwanted ingredient list]",
            "💪 [NUTRITION] — [Key nutrient] per serving for [health benefit]",
            "📦 [FRESHNESS] — [Packaging method] locks in [quality] for [shelf life]",
            "👨‍🍳 [VERSATILE] — Perfect for [use1], [use2], and [use3]",
        ],
        description_structure=[
            "Taste/origin story",
            "Nutrition facts highlight",
            "Ingredient sourcing story",
            "Usage suggestions / recipes",
            "Allergen information",
            "Storage instructions",
        ],
        seo_keywords_hints=["diet type (keto/vegan)", "allergen-free", "flavor",
                            "origin country", "organic certification", "meal type"],
        avoid_words=["health claims without evidence", "cure/treat (FDA regulated)",
                     "best tasting (subjective without proof)"],
        emoji_palette=["😋", "🍳", "🥗", "☕", "🍫", "🌿", "🥜", "🍯", "🧂", "🫒"],
        typical_features=["serving size", "calories", "certifications", "allergen info",
                         "shelf life", "storage requirements"],
        target_audiences=["health-conscious consumers", "keto dieters", "vegans",
                         "foodies", "meal preppers", "parents"],
    ),

    Category.AUTOMOTIVE: CategoryTemplate(
        category=Category.AUTOMOTIVE,
        name="Automotive & Parts",
        description="Car parts, accessories, tools, motorcycle, maintenance",
        power_words=_AUTOMOTIVE_WORDS,
        title_patterns=[
            "[Brand] [Product] for [Vehicle Make/Model] [Year Range] - [Spec] [Certification]",
            "[Adjective] [Product] [Spec] - [Fitment] [Material]",
            "[Product] Kit [Piece Count] - [Vehicle Type] [Application]",
        ],
        bullet_patterns=[
            "🔧 [FITMENT] — Direct fit for [vehicle list], no modification needed",
            "🛡️ [DURABILITY] — [Material] construction rated for [miles/years]",
            "⚡ [PERFORMANCE] — [Improvement metric] over stock [part]",
            "📦 [COMPLETE KIT] — Includes [components], hardware, and instructions",
            "✅ [CERTIFIED] — Meets or exceeds [OEM/SAE/DOT] standards",
        ],
        description_structure=[
            "Fitment/compatibility chart",
            "Performance improvement details",
            "Installation guide overview",
            "Material & engineering specs",
            "Warranty information",
            "Vehicle compatibility list",
        ],
        seo_keywords_hints=["vehicle make model year", "OEM part number", "application type",
                            "vs OEM comparison", "installation keyword"],
        avoid_words=["racing only (unless true)", "universal (be specific)"],
        emoji_palette=["🔧", "🚗", "⚡", "🛡️", "🏎️", "🔩", "🛞", "🏍️", "🚙", "⛽"],
        typical_features=["compatibility", "material", "certification", "warranty",
                         "installation difficulty", "included components"],
        target_audiences=["DIY mechanics", "car enthusiasts", "fleet managers",
                         "daily commuters", "off-road enthusiasts"],
    ),

    Category.PET: CategoryTemplate(
        category=Category.PET,
        name="Pet Supplies",
        description="Dog, cat, fish, bird supplies, food, toys, grooming",
        power_words=_PET_WORDS,
        title_patterns=[
            "[Brand] [Product] for [Pet Type] - [Size] [Feature] [Benefit]",
            "[Adjective] [Product] [Pet Size] - [Material] [Safety Cert]",
            "[Product] [Variant] for [Breed Size] [Pet Type] - [Feature]",
        ],
        bullet_patterns=[
            "🐾 [PET APPROVED] — [Pet type] love the [feature] design",
            "🛡️ [SAFE] — [Material] that's [safety feature], [certification]",
            "🧹 [EASY CLEAN] — [Cleaning method] in [time] for busy pet parents",
            "📏 [SIZE GUIDE] — Perfect for [breed size]: [weight range] [pet type]",
            "💚 [HEALTH] — Supports [health aspect] with [ingredient/feature]",
        ],
        description_structure=[
            "Pet lifestyle story",
            "Product features & benefits",
            "Size/breed compatibility",
            "Safety & materials",
            "Care instructions",
            "Vet recommendation note",
        ],
        seo_keywords_hints=["pet type", "breed", "pet size (small/medium/large)",
                            "health concern", "age (puppy/senior)", "flavor"],
        avoid_words=["cure (vet-regulated)", "human food (unless verified)"],
        emoji_palette=["🐾", "🐕", "🐈", "🦴", "🐟", "🦜", "🧸", "💚", "🥩", "🏠"],
        typical_features=["pet size/weight range", "material", "flavor", "safety cert",
                         "durability rating", "cleaning method"],
        target_audiences=["new pet owners", "multi-pet households", "senior pet parents",
                         "breed-specific owners", "pet health enthusiasts"],
    ),

    Category.OFFICE: CategoryTemplate(
        category=Category.OFFICE,
        name="Office & School Supplies",
        description="Stationery, desk accessories, printer supplies, planners",
        power_words=_OFFICE_WORDS,
        title_patterns=[
            "[Brand] [Product] [Quantity] Pack - [Feature] for [Use Case]",
            "[Adjective] [Product] [Color/Style] - [Compatibility] [Size]",
            "[Product] Set [Piece Count] - [Professional/Student] [Feature]",
        ],
        bullet_patterns=[
            "📎 [PROFESSIONAL] — [Quality detail] for [professional context]",
            "📦 [VALUE] — [Quantity] count at [value proposition]",
            "✅ [COMPATIBLE] — Works with [device/system list]",
            "🎨 [DESIGN] — [Aesthetic feature] elevates your [workspace type]",
            "♻️ [ECO] — Made from [sustainable material], [certification]",
        ],
        description_structure=[
            "Productivity benefit intro",
            "Product specifications",
            "Compatibility details",
            "Pack contents",
            "Use case suggestions",
            "Environmental credentials",
        ],
        seo_keywords_hints=["office type (home/corporate)", "device compatibility",
                            "quantity keyword", "use case (school/work)", "organization type"],
        avoid_words=["generic", "basic", "cheap alternative"],
        emoji_palette=["📎", "📝", "🖊️", "📋", "🗂️", "📐", "🖨️", "📚", "💼", "🎨"],
        typical_features=["quantity", "compatibility", "material", "dimensions",
                         "eco-credentials", "color options"],
        target_audiences=["remote workers", "students", "teachers", "office managers",
                         "planners/organizers"],
    ),

    Category.BABY: CategoryTemplate(
        category=Category.BABY,
        name="Baby & Toddler",
        description="Baby gear, clothing, feeding, nursery, safety products",
        power_words=_BABY_WORDS,
        title_patterns=[
            "[Brand] [Product] for [Age Range] - [Safety Cert] [Feature] [Color]",
            "[Adjective] [Product] [Style] - [Certification] [Material]",
            "[Product] [Size] for [Stage] Baby - [Feature1] & [Feature2]",
        ],
        bullet_patterns=[
            "👶 [SAFE] — [Certification] certified, [tested detail]",
            "💚 [GENTLE] — [Material] that's [safety feature] for delicate skin",
            "🔄 [GROWS WITH BABY] — [Convertible feature] from [stage1] to [stage2]",
            "🧹 [EASY CLEAN] — [Washable feature] for inevitable messes",
            "🎁 [REGISTRY ESSENTIAL] — #1 pick for [occasion] by [authority]",
        ],
        description_structure=[
            "Parent reassurance opening",
            "Safety certifications detail",
            "Age/stage compatibility",
            "Materials & construction",
            "Easy-of-use features",
            "What's in the box",
        ],
        seo_keywords_hints=["age/stage (newborn/infant/toddler)", "safety standard",
                            "milestone (crawling/walking)", "registry keywords", "organic/natural"],
        avoid_words=["cheap", "adult use", "unsupervised", "cure/treat (medical claims)"],
        emoji_palette=["👶", "🍼", "🧸", "💚", "🌙", "⭐", "🎀", "🧷", "🚼", "🎁"],
        typical_features=["age range", "weight limit", "safety certifications", "material",
                         "assembly required", "convertible stages"],
        target_audiences=["new parents", "expecting parents", "grandparents",
                         "baby shower gifters", "daycare providers"],
    ),

    Category.HEALTH: CategoryTemplate(
        category=Category.HEALTH,
        name="Health & Wellness",
        description="Supplements, vitamins, medical devices, wellness products",
        power_words=_HEALTH_WORDS,
        title_patterns=[
            "[Brand] [Product] [Strength] - [Key Ingredient] [Serving Count] [Certification]",
            "[Adjective] [Product] [Form] - [Benefit] Support [Certification]",
            "[Product] [Variant] [Strength] - [Dietary Info] [Count] Capsules/Tablets",
        ],
        bullet_patterns=[
            "💊 [FORMULA] — [Strength] of [ingredient] per serving for [benefit]",
            "✅ [CERTIFIED] — [Certification] in [facility type], third-party tested",
            "🌿 [CLEAN] — [Dietary info]: No [unwanted additive list]",
            "📊 [SCIENCE] — Backed by [study count] clinical studies on [ingredient]",
            "💰 [VALUE] — [Count] servings = [months] supply at [per-day cost]",
        ],
        description_structure=[
            "Health benefit introduction",
            "Key ingredients & dosage",
            "Clinical evidence summary",
            "How to take / dosage guide",
            "Allergen & dietary info",
            "Certifications & testing",
        ],
        seo_keywords_hints=["health concern", "ingredient name", "dosage", "form (capsule/gummy)",
                            "dietary restriction", "certification"],
        avoid_words=["cure", "treat", "diagnose", "prevent disease",
                     "FDA approved (unless actually approved drug)", "miracle"],
        emoji_palette=["💊", "🌿", "💪", "🧬", "❤️", "🧘", "⚡", "🧪", "📊", "✅"],
        typical_features=["serving count", "dosage per serving", "certifications",
                         "form factor", "dietary restrictions", "expiration"],
        target_audiences=["health-conscious adults", "athletes", "seniors",
                         "women's health", "men's health", "keto/paleo dieters"],
    ),
}


# =============================================================================
# Template engine: apply category knowledge to listing generation
# =============================================================================

class TemplateEngine:
    """Apply category templates to enhance listing generation."""

    def __init__(self):
        self.templates = CATEGORY_TEMPLATES

    @property
    def categories(self) -> list[str]:
        """List all available categories."""
        return [c.value for c in Category]

    def get_template(self, category: str) -> Optional[CategoryTemplate]:
        """Get template by category name."""
        try:
            cat = Category(category.lower())
            return self.templates.get(cat)
        except ValueError:
            return None

    def detect_category(self, product_name: str) -> Optional[Category]:
        """Auto-detect product category from product name/description."""
        import re
        product_lower = product_name.lower()

        keyword_map: dict[Category, list[str]] = {
            Category.ELECTRONICS: ["phone", "iphone", "smartphone", "laptop", "tablet",
                                   "headphone", "headphones", "earphone", "earphones", "earbud",
                                   "speaker", "charger", "cable", "bluetooth", "wireless",
                                   "camera", "drone", "smartwatch", "keyboard", "mouse",
                                   "monitor", "tv", "projector", "power bank", "usb",
                                   "gpu", "cpu", "ssd", "router", "modem", "console"],
            Category.FASHION: ["shirt", "dress", "pants", "jeans", "jacket", "coat",
                              "sweater", "hoodie", "skirt", "shoes", "boots", "sneakers",
                              "sandals", "hat", "cap", "scarf", "gloves", "bag", "purse",
                              "wallet", "sunglasses", "watch", "ring", "necklace",
                              "bracelet", "earrings", "belt", "socks", "underwear"],
            Category.HOME_GARDEN: ["furniture", "table", "chair", "shelf", "lamp",
                                   "curtain", "rug", "pillow", "blanket", "towel",
                                   "kitchen", "cookware", "pan", "pot", "knife",
                                   "garden", "plant", "flower", "tool set", "organizer",
                                   "storage", "basket", "vase", "candle", "mirror"],
            Category.BEAUTY: ["serum", "cream", "moisturizer", "cleanser", "sunscreen",
                             "makeup", "lipstick", "mascara", "foundation", "concealer",
                             "shampoo", "conditioner", "hair", "nail", "perfume",
                             "skincare", "face mask", "toner", "exfoliant", "eye cream"],
            Category.SPORTS: ["yoga", "dumbbell", "resistance band", "gym", "fitness",
                             "running", "cycling", "camping", "hiking", "tennis",
                             "basketball", "football", "soccer", "swimming", "surfing",
                             "climbing", "fishing", "golf", "skateboard", "boxing",
                             "workout", "exercise", "kettlebell", "barbell", "treadmill"],
            Category.TOYS: ["toy", "lego", "puzzle", "doll", "action figure",
                           "board game", "card game", "playset", "stuffed animal",
                           "building blocks", "rc car", "nerf", "slime", "craft kit"],
            Category.FOOD: ["coffee", "tea", "chocolate", "snack", "protein",
                           "organic", "spice", "sauce", "oil", "honey", "nut",
                           "dried fruit", "powder", "cereal", "granola", "jerky"],
            Category.AUTOMOTIVE: ["car", "vehicle", "tire", "brake", "engine",
                                 "motor", "headlight", "bumper", "exhaust", "filter",
                                 "wiper", "dash cam", "gps", "car charger", "seat cover"],
            Category.PET: ["dog", "cat", "pet", "puppy", "kitten", "fish tank",
                          "aquarium", "bird", "leash", "collar", "pet food",
                          "litter", "pet bed", "chew toy", "grooming"],
            Category.OFFICE: ["pen", "pencil", "notebook", "planner", "stapler",
                             "printer", "ink", "toner", "label", "folder",
                             "binder", "desk", "whiteboard", "sticky note", "tape"],
            Category.BABY: ["baby", "infant", "toddler", "diaper", "stroller",
                           "car seat", "crib", "bottle", "pacifier", "teething",
                           "baby food", "onesie", "nursery", "swaddle", "bib"],
            Category.HEALTH: ["supplement", "vitamin", "probiotic", "collagen",
                             "omega", "magnesium", "zinc", "iron", "calcium",
                             "melatonin", "cbd", "essential oil", "thermometer",
                             "blood pressure", "first aid", "bandage", "brace",
                             "capsule", "tablet supplement", "dietary", "herbal"],
        }

        def _word_match(keyword: str, text: str) -> bool:
            """Match keyword with smart boundary detection.
            
            Uses word boundaries to prevent false partial matches like
            'table' in 'adjustable'. For compound words like 'iphone'
            containing 'phone', add the compound form to the keyword list.
            """
            return bool(re.search(r'\b' + re.escape(keyword) + r'\b', text))

        scores: dict[Category, int] = {}
        for cat, keywords in keyword_map.items():
            score = sum(1 for kw in keywords if _word_match(kw, product_lower))
            if score > 0:
                scores[cat] = score

        if scores:
            return max(scores, key=scores.get)
        return None

    def enhance_prompt(self, product: str, platform: str,
                       category: Optional[str] = None,
                       language: str = "English") -> str:
        """Generate an enhanced prompt using category template knowledge."""
        if category:
            try:
                cat = Category(category.lower())
            except ValueError:
                cat = self.detect_category(product)
        else:
            cat = self.detect_category(product)

        if not cat or cat not in self.templates:
            return ""

        tmpl = self.templates[cat]
        pw = tmpl.power_words

        sections = [
            f"## Category Intelligence: {tmpl.name}",
            "",
            f"### Recommended Title Patterns",
            *[f"- {p}" for p in tmpl.title_patterns],
            "",
            f"### Bullet Point Patterns",
            *[f"- {p}" for p in tmpl.bullet_patterns],
            "",
            f"### Description Structure",
            *[f"{i+1}. {s}" for i, s in enumerate(tmpl.description_structure)],
            "",
            f"### Power Words to Use",
            f"- Urgency: {', '.join(pw.urgency[:4])}",
            f"- Trust: {', '.join(pw.trust[:4])}",
            f"- Value: {', '.join(pw.value[:4])}",
            f"- Emotion: {', '.join(pw.emotion[:4])}",
            f"- Technical: {', '.join(pw.technical[:4])}",
            "",
            f"### SEO Keyword Hints",
            *[f"- Include: {h}" for h in tmpl.seo_keywords_hints],
            "",
            f"### Words to AVOID",
            *[f"- ❌ {w}" for w in tmpl.avoid_words],
            "",
            f"### Emoji Palette: {' '.join(tmpl.emoji_palette[:6])}",
        ]

        # Platform-specific tips
        platform_lower = platform.lower().replace(" ", "_")
        if platform_lower in tmpl.platform_tips:
            sections.extend([
                "",
                f"### Platform Tips ({platform})",
                *[f"- 💡 {tip}" for tip in tmpl.platform_tips[platform_lower]],
            ])

        # Target audiences
        if tmpl.target_audiences:
            sections.extend([
                "",
                f"### Target Audiences",
                *[f"- 🎯 {a}" for a in tmpl.target_audiences],
            ])

        return "\n".join(sections)

    def get_power_words(self, category: str,
                        word_type: Optional[str] = None,
                        limit: int = 10) -> list[str]:
        """Get power words for a category, optionally filtered by type."""
        tmpl = self.get_template(category)
        if not tmpl:
            return []

        pw = tmpl.power_words
        if word_type:
            words = getattr(pw, word_type.lower(), [])
            return words[:limit]

        # Mix from all types
        all_words = (pw.urgency + pw.trust + pw.value + pw.emotion + pw.technical)
        return all_words[:limit]

    def get_emoji_palette(self, category: str) -> list[str]:
        """Get recommended emojis for a category."""
        tmpl = self.get_template(category)
        return tmpl.emoji_palette if tmpl else []

    def format_category_summary(self, category: str) -> str:
        """Format a human-readable category summary."""
        tmpl = self.get_template(category)
        if not tmpl:
            return f"Unknown category: {category}"

        pw = tmpl.power_words
        lines = [
            f"📂 **{tmpl.name}**",
            f"_{tmpl.description}_",
            "",
            f"🎯 Audiences: {', '.join(tmpl.target_audiences[:4])}",
            f"🏷️ Features: {', '.join(tmpl.typical_features[:5])}",
            f"✨ Emojis: {' '.join(tmpl.emoji_palette[:6])}",
            f"💬 Power words: {len(pw.urgency + pw.trust + pw.value + pw.emotion + pw.technical)} total",
            f"📝 Title patterns: {len(tmpl.title_patterns)}",
            f"📋 Bullet patterns: {len(tmpl.bullet_patterns)}",
        ]
        return "\n".join(lines)
