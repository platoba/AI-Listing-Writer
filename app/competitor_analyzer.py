"""
竞品分析模块 - 抓取并分析竞品listing
"""
import re
from typing import Dict, List, Optional
from dataclasses import dataclass
import httpx
from bs4 import BeautifulSoup


@dataclass
class CompetitorListing:
    """竞品listing数据结构"""
    platform: str
    title: str
    price: Optional[float]
    rating: Optional[float]
    reviews_count: Optional[int]
    bullets: List[str]
    description: str
    keywords: List[str]
    url: str


class CompetitorAnalyzer:
    """竞品分析器"""
    
    def __init__(self, proxy: Optional[str] = None):
        self.proxy = proxy
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
        }
    
    async def analyze_amazon_asin(self, asin: str, marketplace: str = 'com') -> CompetitorListing:
        """分析Amazon ASIN"""
        url = f'https://www.amazon.{marketplace}/dp/{asin}'
        async with httpx.AsyncClient(proxies=self.proxy, headers=self.headers, timeout=30) as client:
            resp = await client.get(url)
            soup = BeautifulSoup(resp.text, 'html.parser')
            
            title = soup.select_one('#productTitle')
            title_text = title.get_text(strip=True) if title else ''
            
            price_elem = soup.select_one('.a-price .a-offscreen')
            price = self._parse_price(price_elem.get_text() if price_elem else None)
            
            rating_elem = soup.select_one('.a-icon-star .a-icon-alt')
            rating = float(rating_elem.get_text().split()[0]) if rating_elem else None
            
            reviews_elem = soup.select_one('#acrCustomerReviewText')
            reviews = int(re.sub(r'\D', '', reviews_elem.get_text())) if reviews_elem else None
            
            bullets = [li.get_text(strip=True) for li in soup.select('#feature-bullets li span.a-list-item')]
            
            desc_elem = soup.select_one('#productDescription')
            description = desc_elem.get_text(strip=True) if desc_elem else ''
            
            keywords = self._extract_keywords(title_text + ' ' + ' '.join(bullets))
            
            return CompetitorListing(
                platform='Amazon',
                title=title_text,
                price=price,
                rating=rating,
                reviews_count=reviews,
                bullets=bullets,
                description=description,
                keywords=keywords,
                url=url
            )
    
    async def analyze_shopee_url(self, url: str) -> CompetitorListing:
        """分析Shopee商品"""
        # 从URL提取shop_id和item_id
        match = re.search(r'i\.(\d+)\.(\d+)', url)
        if not match:
            raise ValueError('Invalid Shopee URL')
        
        shop_id, item_id = match.groups()
        api_url = f'https://shopee.sg/api/v4/item/get?itemid={item_id}&shopid={shop_id}'
        
        async with httpx.AsyncClient(proxies=self.proxy, headers=self.headers, timeout=30) as client:
            resp = await client.get(api_url)
            data = resp.json()['data']
            
            return CompetitorListing(
                platform='Shopee',
                title=data['name'],
                price=data['price'] / 100000,  # Shopee价格单位
                rating=data.get('item_rating', {}).get('rating_star'),
                reviews_count=data.get('cmt_count'),
                bullets=[],
                description=data.get('description', ''),
                keywords=self._extract_keywords(data['name']),
                url=url
            )
    
    def compare_listings(self, my_listing: Dict, competitors: List[CompetitorListing]) -> Dict:
        """对比分析"""
        avg_price = sum(c.price for c in competitors if c.price) / len([c for c in competitors if c.price])
        avg_rating = sum(c.rating for c in competitors if c.rating) / len([c for c in competitors if c.rating])
        
        common_keywords = set()
        for comp in competitors:
            common_keywords.update(comp.keywords)
        
        my_keywords = set(self._extract_keywords(my_listing.get('title', '')))
        missing_keywords = common_keywords - my_keywords
        
        return {
            'price_benchmark': {
                'average': round(avg_price, 2),
                'min': min(c.price for c in competitors if c.price),
                'max': max(c.price for c in competitors if c.price),
            },
            'rating_benchmark': round(avg_rating, 2),
            'total_reviews': sum(c.reviews_count or 0 for c in competitors),
            'common_keywords': list(common_keywords)[:20],
            'missing_keywords': list(missing_keywords)[:10],
            'title_length_avg': sum(len(c.title) for c in competitors) // len(competitors),
            'bullets_count_avg': sum(len(c.bullets) for c in competitors) // len(competitors),
        }
    
    def _parse_price(self, price_str: Optional[str]) -> Optional[float]:
        """解析价格字符串"""
        if not price_str:
            return None
        match = re.search(r'[\d,]+\.?\d*', price_str.replace(',', ''))
        return float(match.group()) if match else None
    
    def _extract_keywords(self, text: str) -> List[str]:
        """提取关键词（简单版）"""
        words = re.findall(r'\b[a-zA-Z]{3,}\b', text.lower())
        stopwords = {'the', 'and', 'for', 'with', 'this', 'that', 'from', 'your', 'are', 'has'}
        return [w for w in words if w not in stopwords][:30]
