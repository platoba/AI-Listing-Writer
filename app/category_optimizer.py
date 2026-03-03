"""Category Optimizer for product listings.

Auto-categorization, browse node mapping, and cross-platform category
recommendations for e-commerce product listings.

Features:
- Keyword-based category detection for 8 platforms
- Browse node suggestion for Amazon marketplace
- Cross-platform category mapping
- Category compliance validation
- Category depth optimization
- Subcategory recommendation engine
"""

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class CategoryMatch:
    category: str
    subcategory: str = ""
    confidence: float = 0.0  # 0-1
    browse_node: str = ""
    path: list[str] = field(default_factory=list)
    matched_keywords: list[str] = field(default_factory=list)


@dataclass
class CategorySuggestion:
    platform: str
    primary: CategoryMatch
    alternatives: list[CategoryMatch] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    tips: list[str] = field(default_factory=list)


@dataclass
class CrossPlatformMapping:
    source_platform: str
    source_category: str
    mappings: dict[str, CategoryMatch] = field(default_factory=dict)  # platform -> match

    def summary(self) -> str:
        lines = [
            "🗂️ Cross-Platform Category Mapping",
            f"Source: {self.source_platform} → {self.source_category}",
            "",
        ]
        for platform, match in sorted(self.mappings.items()):
            path_str = " > ".join(match.path) if match.path else match.category
            lines.append(f"  {platform:15s} → {path_str} ({match.confidence:.0%})")
            if match.browse_node:
                lines.append(f"  {'':15s}   Node: {match.browse_node}")
        return "\n".join(lines)


# ── Category Taxonomy ──────────────────────────────────────

# Unified category taxonomy with keyword triggers
CATEGORY_TAXONOMY = {
    "Electronics": {
        "keywords": ["electronic", "phone", "laptop", "tablet", "computer", "headphone",
                      "speaker", "cable", "charger", "battery", "camera", "drone",
                      "smartwatch", "earphone", "earbuds", "bluetooth", "usb", "hdmi",
                      "keyboard", "mouse", "monitor", "gpu", "cpu", "ssd", "ram",
                      "电子", "手机", "电脑", "耳机", "充电", "数码", "智能手表"],
        "subcategories": {
            "Mobile Phones & Accessories": ["phone", "case", "screen protector", "charger", "手机", "手机壳"],
            "Computers & Peripherals": ["laptop", "keyboard", "mouse", "monitor", "computer", "电脑", "键盘"],
            "Audio & Headphones": ["headphone", "earphone", "earbuds", "speaker", "耳机", "音箱"],
            "Cameras & Photography": ["camera", "lens", "tripod", "drone", "相机", "镜头"],
            "Smart Home": ["smart home", "alexa", "google home", "智能家居", "智能音箱"],
            "Wearables": ["smartwatch", "fitness tracker", "band", "智能手表", "手环"],
            "Cables & Adapters": ["cable", "adapter", "usb", "hdmi", "充电线", "转接头"],
        },
    },
    "Clothing & Fashion": {
        "keywords": ["shirt", "dress", "pants", "jacket", "shoe", "boot", "sneaker",
                      "hat", "scarf", "glove", "sock", "underwear", "bra", "coat",
                      "sweater", "hoodie", "jeans", "skirt", "suit", "tie", "belt",
                      "衣服", "裤子", "鞋", "帽子", "外套", "连衣裙", "卫衣"],
        "subcategories": {
            "Men's Clothing": ["men", "men's", "male", "man", "男装", "男士"],
            "Women's Clothing": ["women", "women's", "female", "woman", "lady", "女装", "女士"],
            "Shoes & Footwear": ["shoe", "boot", "sneaker", "sandal", "slipper", "鞋"],
            "Accessories": ["hat", "scarf", "glove", "belt", "tie", "wallet", "帽子", "围巾"],
            "Activewear": ["yoga", "gym", "sport", "running", "athletic", "运动"],
            "Children's Clothing": ["kid", "children", "baby", "boy", "girl", "童装", "儿童"],
        },
    },
    "Home & Garden": {
        "keywords": ["furniture", "bed", "sofa", "table", "chair", "lamp", "curtain",
                      "rug", "pillow", "blanket", "kitchen", "bathroom", "garden",
                      "tool", "storage", "organizer", "shelf", "decor", "vase",
                      "家具", "床", "沙发", "灯", "厨房", "花园", "收纳"],
        "subcategories": {
            "Furniture": ["furniture", "bed", "sofa", "table", "chair", "desk", "家具"],
            "Kitchen & Dining": ["kitchen", "pot", "pan", "knife", "cutting board", "厨房", "餐具"],
            "Bathroom": ["bathroom", "shower", "towel", "soap", "浴室", "毛巾"],
            "Bedding": ["bedding", "pillow", "blanket", "sheet", "duvet", "床品", "枕头"],
            "Lighting": ["lamp", "light", "bulb", "chandelier", "灯", "照明"],
            "Garden & Outdoor": ["garden", "plant", "pot", "outdoor", "patio", "花园", "户外"],
            "Storage & Organization": ["storage", "organizer", "shelf", "rack", "bin", "收纳"],
            "Home Decor": ["decor", "wall art", "frame", "vase", "candle", "装饰"],
        },
    },
    "Beauty & Personal Care": {
        "keywords": ["makeup", "skincare", "hair", "perfume", "cream", "serum",
                      "lipstick", "mascara", "foundation", "shampoo", "conditioner",
                      "sunscreen", "moisturizer", "cleanser", "face mask", "nail",
                      "化妆", "护肤", "美妆", "香水", "面膜", "洗发", "防晒"],
        "subcategories": {
            "Skincare": ["skincare", "serum", "moisturizer", "cleanser", "cream", "护肤", "面霜"],
            "Makeup": ["makeup", "lipstick", "foundation", "mascara", "eyeshadow", "化妆", "口红"],
            "Hair Care": ["shampoo", "conditioner", "hair", "洗发", "护发"],
            "Fragrances": ["perfume", "cologne", "fragrance", "香水"],
            "Nail Care": ["nail", "polish", "manicure", "美甲"],
            "Sun Care": ["sunscreen", "spf", "uv", "防晒"],
            "Tools & Accessories": ["brush", "sponge", "mirror", "化妆刷", "工具"],
        },
    },
    "Sports & Outdoors": {
        "keywords": ["sport", "fitness", "gym", "yoga", "running", "cycling",
                      "camping", "hiking", "fishing", "swimming", "tennis",
                      "basketball", "football", "golf", "skiing", "surfing",
                      "运动", "健身", "瑜伽", "跑步", "露营", "钓鱼"],
        "subcategories": {
            "Exercise & Fitness": ["fitness", "gym", "workout", "dumbbell", "treadmill", "健身"],
            "Outdoor Recreation": ["camping", "hiking", "backpack", "tent", "露营", "登山"],
            "Cycling": ["bike", "bicycle", "cycling", "helmet", "自行车"],
            "Water Sports": ["swimming", "surfing", "diving", "snorkel", "游泳"],
            "Team Sports": ["basketball", "football", "soccer", "volleyball", "篮球", "足球"],
            "Yoga & Pilates": ["yoga", "pilates", "mat", "瑜伽"],
            "Fishing": ["fishing", "rod", "reel", "bait", "钓鱼"],
        },
    },
    "Toys & Games": {
        "keywords": ["toy", "game", "puzzle", "doll", "action figure", "lego",
                      "board game", "card game", "rc car", "building block",
                      "plush", "stuffed", "educational", "toy car",
                      "玩具", "游戏", "积木", "拼图", "娃娃", "益智"],
        "subcategories": {
            "Building Blocks": ["lego", "building block", "construction", "积木"],
            "Dolls & Action Figures": ["doll", "action figure", "barbie", "娃娃"],
            "Board Games": ["board game", "card game", "chess", "桌游"],
            "RC & Remote Control": ["rc", "remote control", "drone", "遥控"],
            "Educational Toys": ["educational", "learning", "stem", "益智"],
            "Plush Toys": ["plush", "stuffed", "teddy", "毛绒"],
            "Outdoor Toys": ["outdoor", "water gun", "bubble", "户外"],
        },
    },
    "Pet Supplies": {
        "keywords": ["pet", "dog", "cat", "fish", "bird", "hamster", "rabbit",
                      "leash", "collar", "food bowl", "litter", "aquarium",
                      "pet bed", "pet toy", "grooming",
                      "宠物", "狗", "猫", "猫粮", "狗粮", "宠物用品"],
        "subcategories": {
            "Dog Supplies": ["dog", "puppy", "canine", "狗"],
            "Cat Supplies": ["cat", "kitten", "feline", "猫"],
            "Fish & Aquarium": ["fish", "aquarium", "tank", "鱼", "水族"],
            "Bird Supplies": ["bird", "cage", "perch", "鸟"],
            "Pet Food": ["pet food", "treat", "chew", "猫粮", "狗粮"],
            "Pet Grooming": ["grooming", "brush", "shampoo", "nail clipper", "美容"],
        },
    },
    "Baby & Kids": {
        "keywords": ["baby", "infant", "toddler", "stroller", "diaper", "bottle",
                      "pacifier", "car seat", "crib", "nursery", "maternity",
                      "baby clothes", "baby food", "teether",
                      "婴儿", "宝宝", "母婴", "奶瓶", "尿布", "推车"],
        "subcategories": {
            "Feeding": ["bottle", "sippy", "high chair", "baby food", "奶瓶", "辅食"],
            "Diapering": ["diaper", "wipe", "changing", "尿布", "尿不湿"],
            "Strollers & Car Seats": ["stroller", "car seat", "carrier", "推车", "安全座椅"],
            "Nursery": ["crib", "nursery", "mobile", "monitor", "婴儿床"],
            "Baby Safety": ["baby gate", "socket cover", "safety", "防护"],
            "Maternity": ["maternity", "pregnancy", "nursing", "孕妇", "哺乳"],
        },
    },
    "Office & School": {
        "keywords": ["office", "desk", "pen", "paper", "printer", "notebook",
                      "stapler", "folder", "envelope", "calculator", "whiteboard",
                      "办公", "文具", "笔", "纸", "打印"],
        "subcategories": {
            "Writing Instruments": ["pen", "pencil", "marker", "highlighter", "笔"],
            "Paper & Notebooks": ["paper", "notebook", "journal", "sticky note", "纸", "本子"],
            "Office Furniture": ["desk", "office chair", "standing desk", "办公桌"],
            "Office Electronics": ["printer", "scanner", "shredder", "打印机"],
            "School Supplies": ["backpack", "school", "ruler", "eraser", "文具", "书包"],
        },
    },
    "Food & Beverages": {
        "keywords": ["food", "snack", "coffee", "tea", "chocolate", "organic",
                      "vitamin", "supplement", "protein", "candy", "spice",
                      "sauce", "oil", "honey",
                      "食品", "零食", "咖啡", "茶", "巧克力", "保健品"],
        "subcategories": {
            "Coffee & Tea": ["coffee", "tea", "espresso", "matcha", "咖啡", "茶"],
            "Snacks": ["snack", "chip", "cracker", "nut", "零食", "坚果"],
            "Health Supplements": ["vitamin", "supplement", "protein", "probiotic", "保健品"],
            "Organic & Natural": ["organic", "natural", "gluten-free", "vegan", "有机"],
            "Condiments & Spices": ["spice", "sauce", "seasoning", "oil", "调料"],
            "Candy & Sweets": ["candy", "chocolate", "gummy", "糖果", "巧克力"],
        },
    },
    "Automotive": {
        "keywords": ["car", "auto", "vehicle", "tire", "engine", "motor",
                      "dashboard", "gps", "seat cover", "floor mat",
                      "wiper", "oil", "brake", "headlight",
                      "汽车", "车载", "轮胎", "发动机", "车用"],
        "subcategories": {
            "Car Electronics": ["car stereo", "dashcam", "gps", "car charger", "车载"],
            "Exterior Accessories": ["car cover", "wiper", "headlight", "外饰"],
            "Interior Accessories": ["seat cover", "floor mat", "steering", "内饰"],
            "Car Care": ["car wash", "wax", "polish", "detailing", "洗车"],
            "Tires & Wheels": ["tire", "wheel", "rim", "轮胎"],
            "Parts & Tools": ["brake", "filter", "oil", "tool", "配件"],
        },
    },
}

# ── Amazon Browse Nodes ────────────────────────────────────

AMAZON_BROWSE_NODES = {
    "Electronics": {
        "node": "172282",
        "subcategories": {
            "Mobile Phones & Accessories": "2407749011",
            "Computers & Peripherals": "172456",
            "Audio & Headphones": "172541",
            "Cameras & Photography": "172421",
            "Smart Home": "6563140011",
            "Wearables": "7936683011",
        },
    },
    "Clothing & Fashion": {
        "node": "7141123011",
        "subcategories": {
            "Men's Clothing": "7147441011",
            "Women's Clothing": "7147440011",
            "Shoes & Footwear": "679255011",
        },
    },
    "Home & Garden": {
        "node": "1055398",
        "subcategories": {
            "Furniture": "1063306",
            "Kitchen & Dining": "284507",
            "Bedding": "1063252",
            "Lighting": "495224",
        },
    },
    "Beauty & Personal Care": {
        "node": "3760911",
        "subcategories": {
            "Skincare": "11060451",
            "Makeup": "11058281",
            "Hair Care": "11057241",
        },
    },
    "Sports & Outdoors": {
        "node": "3375251",
        "subcategories": {
            "Exercise & Fitness": "3407731",
            "Outdoor Recreation": "706814011",
            "Cycling": "3405071",
        },
    },
    "Toys & Games": {
        "node": "165793011",
        "subcategories": {
            "Building Blocks": "166092011",
            "Board Games": "166220011",
            "Educational Toys": "166269011",
        },
    },
    "Baby & Kids": {
        "node": "165796011",
        "subcategories": {
            "Feeding": "166759011",
            "Diapering": "166764011",
            "Strollers & Car Seats": "166835011",
        },
    },
    "Pet Supplies": {
        "node": "2619533011",
        "subcategories": {
            "Dog Supplies": "2619534011",
            "Cat Supplies": "2619536011",
        },
    },
}

# ── Platform-Specific Category Names ──────────────────────

PLATFORM_CATEGORY_NAMES = {
    "shopee": {
        "Electronics": "Electronic Devices",
        "Clothing & Fashion": "Men's Wear|Women's Clothes",
        "Home & Garden": "Home & Living",
        "Beauty & Personal Care": "Beauty & Personal Care",
        "Sports & Outdoors": "Sports & Travel",
        "Toys & Games": "Toys, Kids & Babies",
        "Pet Supplies": "Pets",
        "Baby & Kids": "Toys, Kids & Babies",
        "Food & Beverages": "Food & Beverages",
        "Automotive": "Automotive",
    },
    "lazada": {
        "Electronics": "Electronic Devices",
        "Clothing & Fashion": "Fashion",
        "Home & Garden": "Home & Living",
        "Beauty & Personal Care": "Health & Beauty",
        "Sports & Outdoors": "Sports & Outdoors",
        "Toys & Games": "Toys & Games",
        "Baby & Kids": "Mother & Baby",
        "Pet Supplies": "Pet Supplies",
    },
    "aliexpress": {
        "Electronics": "Consumer Electronics",
        "Clothing & Fashion": "Men's Clothing|Women's Clothing",
        "Home & Garden": "Home & Garden",
        "Beauty & Personal Care": "Beauty & Health",
        "Sports & Outdoors": "Sports & Entertainment",
        "Toys & Games": "Toys & Hobbies",
        "Automotive": "Automobiles & Motorcycles",
    },
    "ebay": {
        "Electronics": "Consumer Electronics",
        "Clothing & Fashion": "Clothing, Shoes & Accessories",
        "Home & Garden": "Home & Garden",
        "Beauty & Personal Care": "Health & Beauty",
        "Sports & Outdoors": "Sporting Goods",
        "Toys & Games": "Toys & Hobbies",
        "Automotive": "eBay Motors",
        "Baby & Kids": "Baby",
        "Pet Supplies": "Pet Supplies",
    },
    "walmart": {
        "Electronics": "Electronics",
        "Clothing & Fashion": "Clothing",
        "Home & Garden": "Home",
        "Beauty & Personal Care": "Beauty",
        "Sports & Outdoors": "Sports & Outdoors",
        "Toys & Games": "Toys",
        "Baby & Kids": "Baby",
        "Pet Supplies": "Pets",
        "Food & Beverages": "Food",
        "Automotive": "Auto & Tires",
    },
    "amazon": {
        "Electronics": "Electronics",
        "Clothing & Fashion": "Clothing, Shoes & Jewelry",
        "Home & Garden": "Home & Kitchen",
        "Beauty & Personal Care": "Beauty & Personal Care",
        "Sports & Outdoors": "Sports & Outdoors",
        "Toys & Games": "Toys & Games",
        "Baby & Kids": "Baby",
        "Pet Supplies": "Pet Supplies",
        "Office & School": "Office Products",
        "Food & Beverages": "Grocery & Gourmet Food",
        "Automotive": "Automotive",
    },
    "etsy": {
        "Electronics": "Electronics & Accessories",
        "Clothing & Fashion": "Clothing",
        "Home & Garden": "Home & Living",
        "Beauty & Personal Care": "Bath & Beauty",
        "Toys & Games": "Toys & Games",
        "Office & School": "Paper & Party Supplies",
    },
    "temu": {
        "Electronics": "Electronics",
        "Clothing & Fashion": "Women's Clothing|Men's Clothing",
        "Home & Garden": "Home & Kitchen",
        "Beauty & Personal Care": "Beauty & Health",
        "Sports & Outdoors": "Sports & Outdoors",
        "Toys & Games": "Toys & Games",
    },
}


# ── Category Optimizer ─────────────────────────────────────

class CategoryOptimizer:
    """Auto-categorization and category optimization engine."""

    def __init__(self):
        pass

    def detect_category(self, title: str, description: str = "",
                         keywords: list[str] = None,
                         platform: str = "amazon") -> CategorySuggestion:
        """Detect the best category for a product listing.

        Args:
            title: Product title.
            description: Product description.
            keywords: Optional keyword list.
            platform: Target platform.

        Returns:
            CategorySuggestion with primary and alternative categories.
        """
        text = f"{title} {description} {' '.join(keywords or [])}".lower()
        matches = self._score_categories(text)

        if not matches:
            return CategorySuggestion(
                platform=platform,
                primary=CategoryMatch(category="Uncategorized", confidence=0),
                warnings=["Could not determine category. Please set manually."],
                tips=["Low confidence — try adding more descriptive keywords to your title and description."],
            )

        # Map to platform-specific names
        primary = matches[0]
        primary = self._map_to_platform(primary, platform)

        alternatives = []
        for m in matches[1:4]:
            mapped = self._map_to_platform(m, platform)
            alternatives.append(mapped)

        # Generate tips
        tips = self._generate_tips(primary, platform)
        warnings = self._generate_warnings(primary, platform, text)

        return CategorySuggestion(
            platform=platform,
            primary=primary,
            alternatives=alternatives,
            warnings=warnings,
            tips=tips,
        )

    def _score_categories(self, text: str) -> list[CategoryMatch]:
        """Score text against all categories."""
        scores = []

        for cat_name, cat_data in CATEGORY_TAXONOMY.items():
            # Main category keyword matches
            main_kws = cat_data["keywords"]
            matched_main = [kw for kw in main_kws if kw.lower() in text]
            main_score = len(matched_main) / len(main_kws) if main_kws else 0

            if main_score == 0:
                continue

            # Find best subcategory
            best_sub = ""
            best_sub_score = 0
            best_sub_kws = []
            for sub_name, sub_kws in cat_data.get("subcategories", {}).items():
                sub_matched = [kw for kw in sub_kws if kw.lower() in text]
                sub_score = len(sub_matched) / len(sub_kws) if sub_kws else 0
                if sub_score > best_sub_score:
                    best_sub_score = sub_score
                    best_sub = sub_name
                    best_sub_kws = sub_matched

            combined = main_score * 0.4 + best_sub_score * 0.6 if best_sub else main_score
            all_matched = matched_main + best_sub_kws

            path = [cat_name]
            if best_sub:
                path.append(best_sub)

            # Get browse node
            browse_node = ""
            if cat_name in AMAZON_BROWSE_NODES:
                node_data = AMAZON_BROWSE_NODES[cat_name]
                if best_sub and best_sub in node_data.get("subcategories", {}):
                    browse_node = node_data["subcategories"][best_sub]
                else:
                    browse_node = node_data["node"]

            scores.append(CategoryMatch(
                category=cat_name,
                subcategory=best_sub,
                confidence=round(combined, 3),
                browse_node=browse_node,
                path=path,
                matched_keywords=all_matched[:10],
            ))

        return sorted(scores, key=lambda x: -x.confidence)

    def _map_to_platform(self, match: CategoryMatch, platform: str) -> CategoryMatch:
        """Map generic category to platform-specific name."""
        platform_names = PLATFORM_CATEGORY_NAMES.get(platform.lower(), {})
        platform_cat = platform_names.get(match.category, match.category)

        # Handle split categories (e.g., "Men's Wear|Women's Clothes")
        if "|" in platform_cat:
            # Try to infer from subcategory
            parts = platform_cat.split("|")
            sub_lower = match.subcategory.lower()
            if "men" in sub_lower:
                platform_cat = parts[0]
            elif "women" in sub_lower:
                platform_cat = parts[1] if len(parts) > 1 else parts[0]
            else:
                platform_cat = parts[0]  # default to first

        # Update path with platform-specific names
        mapped_path = [platform_cat]
        if match.subcategory:
            mapped_path.append(match.subcategory)

        return CategoryMatch(
            category=platform_cat,
            subcategory=match.subcategory,
            confidence=match.confidence,
            browse_node=match.browse_node if platform.lower() == "amazon" else "",
            path=mapped_path,
            matched_keywords=match.matched_keywords,
        )

    def cross_platform_map(self, category: str, source_platform: str = "amazon",
                            subcategory: str = "") -> CrossPlatformMapping:
        """Map a category across all platforms.

        Args:
            category: Category name (generic or platform-specific).
            source_platform: Source platform.
            subcategory: Optional subcategory.

        Returns:
            CrossPlatformMapping with mappings for all platforms.
        """
        # Reverse-lookup generic category from platform name
        generic_cat = self._reverse_lookup(category, source_platform)
        if not generic_cat:
            generic_cat = category

        mapping = CrossPlatformMapping(
            source_platform=source_platform,
            source_category=category,
        )

        for platform in PLATFORM_CATEGORY_NAMES:
            platform_names = PLATFORM_CATEGORY_NAMES[platform]
            cat_name = platform_names.get(generic_cat, generic_cat)

            # Resolve split names
            if "|" in cat_name:
                if subcategory and "men" in subcategory.lower():
                    cat_name = cat_name.split("|")[0]
                else:
                    cat_name = cat_name.split("|")[0]

            browse_node = ""
            if platform == "amazon" and generic_cat in AMAZON_BROWSE_NODES:
                node_data = AMAZON_BROWSE_NODES[generic_cat]
                if subcategory and subcategory in node_data.get("subcategories", {}):
                    browse_node = node_data["subcategories"][subcategory]
                else:
                    browse_node = node_data["node"]

            path = [cat_name]
            if subcategory:
                path.append(subcategory)

            mapping.mappings[platform] = CategoryMatch(
                category=cat_name,
                subcategory=subcategory,
                confidence=0.9 if generic_cat in CATEGORY_TAXONOMY else 0.5,
                browse_node=browse_node,
                path=path,
            )

        return mapping

    def _reverse_lookup(self, platform_category: str, platform: str) -> Optional[str]:
        """Find generic category from a platform-specific name."""
        platform_names = PLATFORM_CATEGORY_NAMES.get(platform.lower(), {})
        for generic, name in platform_names.items():
            if platform_category.lower() in name.lower():
                return generic
            for part in name.split("|"):
                if platform_category.lower() == part.lower():
                    return generic
        # Try direct match against taxonomy
        if platform_category in CATEGORY_TAXONOMY:
            return platform_category
        return None

    def validate_category(self, category: str, platform: str,
                           product_data: dict = None) -> dict:
        """Validate if a category is appropriate for the platform.

        Returns:
            Dict with 'valid', 'issues', and 'suggestions'.
        """
        result = {"valid": True, "issues": [], "suggestions": []}

        # Check if category exists on platform
        platform_names = PLATFORM_CATEGORY_NAMES.get(platform.lower(), {})
        all_names = set()
        for name in platform_names.values():
            for part in name.split("|"):
                all_names.add(part.lower())

        if category.lower() not in all_names and category not in CATEGORY_TAXONOMY:
            result["valid"] = False
            result["issues"].append(f"Category '{category}' not found on {platform}")

            # Suggest closest match
            closest = self._find_closest_category(category, all_names)
            if closest:
                result["suggestions"].append(f"Did you mean: {closest}?")

        # Check if product data matches category
        if product_data:
            title = product_data.get("title", "")
            desc = product_data.get("description", "")
            detected = self.detect_category(title, desc, platform=platform)
            if detected.primary.category.lower() != category.lower():
                result["issues"].append(
                    f"Product appears to be in '{detected.primary.category}' "
                    f"(confidence: {detected.primary.confidence:.0%}), not '{category}'"
                )
                result["suggestions"].append(
                    f"Consider: {detected.primary.category} > {detected.primary.subcategory}"
                )

        # Platform-specific rules
        if platform.lower() == "amazon":
            gated_categories = [
                "Grocery & Gourmet Food", "Beauty & Personal Care",
                "Toys & Games", "Automotive",
            ]
            for gated in gated_categories:
                if gated.lower() in category.lower():
                    result["issues"].append(
                        f"'{gated}' may require ungating on Amazon. "
                        "Ensure you have approval before listing."
                    )
                    break

        return result

    def _find_closest_category(self, query: str, categories: set) -> Optional[str]:
        """Find closest matching category name."""
        query_lower = query.lower()
        # Try substring match
        for cat in categories:
            if query_lower in cat or cat in query_lower:
                return cat
        # Try prefix/stem overlap (e.g. "electronic" matches "electronics")
        for cat in categories:
            min_len = min(len(query_lower), len(cat))
            prefix = min_len - 2  # allow 2-char difference
            if prefix >= 4:
                if query_lower[:prefix] in cat or cat[:prefix] in query_lower:
                    return cat
        # Try word overlap
        query_words = set(query_lower.split())
        best = None
        best_overlap = 0
        for cat in categories:
            cat_words = set(cat.split())
            overlap = len(query_words & cat_words)
            # Also check stem overlap (words sharing 4+ char prefix)
            if overlap == 0:
                for qw in query_words:
                    for cw in cat_words:
                        stem = min(len(qw), len(cw)) - 1
                        if stem >= 4 and qw[:stem] == cw[:stem]:
                            overlap += 0.5
            if overlap > best_overlap:
                best_overlap = overlap
                best = cat
        return best if best_overlap > 0 else None

    def _generate_tips(self, match: CategoryMatch, platform: str) -> list[str]:
        """Generate category optimization tips."""
        tips = []

        if match.browse_node and platform.lower() == "amazon":
            tips.append(f"Browse Node ID: {match.browse_node} — use this for flat file uploads")

        if match.subcategory:
            tips.append(
                f"Subcategory '{match.subcategory}' is more specific — "
                "specific categories generally get better visibility"
            )

        if match.confidence < 0.3:
            tips.append(
                "Low confidence match. Consider adding more category-specific "
                "keywords to your title and description."
            )

        if platform.lower() in ("shopee", "lazada"):
            tips.append(
                "Southeast Asian platforms favor deep category paths. "
                "Select the most specific subcategory available."
            )

        if platform.lower() == "etsy":
            tips.append(
                "Etsy uses 'categories + attributes' instead of browse nodes. "
                "Fill all relevant attributes for better search placement."
            )

        return tips

    def _generate_warnings(self, match: CategoryMatch, platform: str,
                            text: str) -> list[str]:
        """Generate category warnings."""
        warnings = []

        # Multi-category product
        scores = self._score_categories(text)
        if len(scores) >= 2 and scores[0].confidence > 0 and scores[1].confidence > 0:
            ratio = scores[1].confidence / scores[0].confidence
            if ratio > 0.8:
                warnings.append(
                    f"Product may fit multiple categories: "
                    f"'{scores[0].category}' and '{scores[1].category}'. "
                    "Consider A/B testing categories."
                )

        # Restricted category warning
        restricted = ["Health & Beauty", "Supplements", "Food", "Grocery"]
        for r in restricted:
            if r.lower() in match.category.lower():
                warnings.append(
                    f"'{match.category}' may have regulatory requirements. "
                    "Ensure compliance with platform policies."
                )
                break

        return warnings

    def suggest_from_asin(self, asin: str, title: str = "",
                           description: str = "") -> CategorySuggestion:
        """Suggest category based on ASIN format and content.

        Useful when you have an Amazon ASIN and want to verify/suggest categories.
        """
        # ASIN prefix patterns (rough heuristic)
        prefix = asin[:2].upper() if len(asin) >= 2 else ""

        # Use text-based detection primarily
        suggestion = self.detect_category(title, description, platform="amazon")

        # Add ASIN tip
        if prefix == "B0":
            suggestion.tips.append(
                f"ASIN {asin} (B0 prefix) — standard product ASIN. "
                "Verify category matches the actual Amazon browse node."
            )

        return suggestion

    def format_suggestion(self, suggestion: CategorySuggestion) -> str:
        """Format category suggestion as readable text."""
        lines = [
            f"🗂️ Category Suggestion for {suggestion.platform.upper()}",
            "",
            f"📌 Primary: {' > '.join(suggestion.primary.path)}",
            f"   Confidence: {suggestion.primary.confidence:.0%}",
        ]

        if suggestion.primary.browse_node:
            lines.append(f"   Browse Node: {suggestion.primary.browse_node}")

        if suggestion.primary.matched_keywords:
            lines.append(f"   Matched: {', '.join(suggestion.primary.matched_keywords[:5])}")

        if suggestion.alternatives:
            lines.append("")
            lines.append("🔄 Alternatives:")
            for alt in suggestion.alternatives:
                lines.append(f"   {' > '.join(alt.path)} ({alt.confidence:.0%})")

        if suggestion.warnings:
            lines.append("")
            lines.append("⚠️ Warnings:")
            for w in suggestion.warnings:
                lines.append(f"   {w}")

        if suggestion.tips:
            lines.append("")
            lines.append("💡 Tips:")
            for t in suggestion.tips:
                lines.append(f"   {t}")

        return "\n".join(lines)


def detect_category(title: str, description: str = "",
                     platform: str = "amazon") -> CategorySuggestion:
    """Convenience function for quick category detection."""
    optimizer = CategoryOptimizer()
    return optimizer.detect_category(title, description, platform=platform)
