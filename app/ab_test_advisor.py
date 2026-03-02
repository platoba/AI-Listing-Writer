"""
A/B测试建议模块 - 基于竞品分析生成测试方案
"""
from typing import Dict, List
from dataclasses import dataclass


@dataclass
class ABTestVariant:
    """A/B测试变体"""
    name: str
    title: str
    bullets: List[str]
    description: str
    hypothesis: str
    expected_impact: str


class ABTestAdvisor:
    """A/B测试顾问"""
    
    def generate_title_variants(self, original_title: str, competitor_analysis: Dict) -> List[ABTestVariant]:
        """生成标题变体"""
        variants = []
        
        # 变体A：添加高频关键词
        missing_kw = competitor_analysis.get('missing_keywords', [])[:3]
        if missing_kw:
            new_title = f"{original_title} - {' '.join(missing_kw).title()}"
            variants.append(ABTestVariant(
                name='Title_A_Keywords',
                title=new_title,
                bullets=[],
                description='',
                hypothesis=f'添加竞品高频关键词 {missing_kw} 可提升搜索曝光',
                expected_impact='CTR +5-10%'
            ))
        
        # 变体B：缩短标题（如果原标题过长）
        avg_len = competitor_analysis.get('title_length_avg', 100)
        if len(original_title) > avg_len * 1.2:
            short_title = ' '.join(original_title.split()[:10])
            variants.append(ABTestVariant(
                name='Title_B_Shorter',
                title=short_title,
                bullets=[],
                description='',
                hypothesis='缩短标题至行业平均长度，提升移动端可读性',
                expected_impact='Mobile CTR +8-12%'
            ))
        
        # 变体C：数字化卖点
        if not any(char.isdigit() for char in original_title):
            numeric_title = original_title.replace('多功能', '10合1').replace('大容量', '5000mAh')
            variants.append(ABTestVariant(
                name='Title_C_Numeric',
                title=numeric_title,
                bullets=[],
                description='',
                hypothesis='添加具体数字增强可信度',
                expected_impact='Conversion +3-7%'
            ))
        
        return variants
    
    def generate_bullet_variants(self, original_bullets: List[str], competitor_analysis: Dict) -> List[ABTestVariant]:
        """生成bullet变体"""
        variants = []
        
        # 变体A：重新排序（痛点优先）
        pain_keywords = ['防水', '耐用', '安全', '保修', 'waterproof', 'durable', 'warranty']
        reordered = sorted(original_bullets, key=lambda b: any(kw in b.lower() for kw in pain_keywords), reverse=True)
        variants.append(ABTestVariant(
            name='Bullets_A_Reorder',
            title='',
            bullets=reordered,
            description='',
            hypothesis='痛点解决方案前置，降低购买顾虑',
            expected_impact='Conversion +4-8%'
        ))
        
        # 变体B：添加社会证明
        social_proof = [f"✓ {b}" for b in original_bullets[:3]] + [
            "⭐ 10,000+ 5-star reviews",
            "🏆 #1 Best Seller in category"
        ]
        variants.append(ABTestVariant(
            name='Bullets_B_SocialProof',
            title='',
            bullets=social_proof,
            description='',
            hypothesis='添加社会证明元素增强信任',
            expected_impact='Conversion +6-10%'
        ))
        
        return variants
    
    def generate_price_test_plan(self, current_price: float, competitor_analysis: Dict) -> Dict:
        """生成价格测试方案"""
        avg_price = competitor_analysis['price_benchmark']['average']
        
        return {
            'current_position': 'above' if current_price > avg_price else 'below',
            'price_gap': round(abs(current_price - avg_price), 2),
            'recommendations': [
                {
                    'variant': 'Price_A_Match',
                    'price': round(avg_price, 2),
                    'hypothesis': '对齐市场均价，测试价格敏感度',
                    'duration': '7 days',
                    'traffic_split': '50/50'
                },
                {
                    'variant': 'Price_B_Premium',
                    'price': round(avg_price * 1.15, 2),
                    'hypothesis': '溢价15%，测试品牌溢价空间',
                    'duration': '7 days',
                    'traffic_split': '30/70'
                },
                {
                    'variant': 'Price_C_Bundle',
                    'price': round(current_price * 1.3, 2),
                    'hypothesis': '捆绑销售（主品+配件），提升客单价',
                    'duration': '14 days',
                    'traffic_split': '20/80'
                }
            ]
        }
    
    def generate_full_test_plan(self, my_listing: Dict, competitor_analysis: Dict) -> Dict:
        """生成完整测试计划"""
        return {
            'title_tests': self.generate_title_variants(my_listing.get('title', ''), competitor_analysis),
            'bullet_tests': self.generate_bullet_variants(my_listing.get('bullets', []), competitor_analysis),
            'price_tests': self.generate_price_test_plan(my_listing.get('price', 0), competitor_analysis),
            'test_sequence': [
                {'week': 1, 'focus': 'Title optimization', 'variants': 3},
                {'week': 2, 'focus': 'Bullet points', 'variants': 2},
                {'week': 3, 'focus': 'Price testing', 'variants': 3},
                {'week': 4, 'focus': 'Winner rollout', 'variants': 1}
            ],
            'success_metrics': [
                'CTR (Click-Through Rate)',
                'Conversion Rate',
                'Average Order Value',
                'Return Rate',
                'Customer Satisfaction Score'
            ]
        }
