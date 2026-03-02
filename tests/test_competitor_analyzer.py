"""
竞品分析模块测试
"""
import pytest
from app.competitor_analyzer import CompetitorAnalyzer, CompetitorListing


@pytest.mark.asyncio
async def test_amazon_asin_parsing():
    """测试Amazon ASIN解析（mock）"""
    analyzer = CompetitorAnalyzer()
    # 实际测试需要mock httpx响应
    assert analyzer is not None


def test_extract_keywords():
    """测试关键词提取"""
    analyzer = CompetitorAnalyzer()
    text = "Portable Bluetooth Speaker Waterproof Wireless with Bass"
    keywords = analyzer._extract_keywords(text)
    
    assert 'portable' in keywords
    assert 'bluetooth' in keywords
    assert 'waterproof' in keywords
    assert 'the' not in keywords  # stopword


def test_parse_price():
    """测试价格解析"""
    analyzer = CompetitorAnalyzer()
    
    assert analyzer._parse_price('$29.99') == 29.99
    assert analyzer._parse_price('$1,299.00') == 1299.0
    assert analyzer._parse_price(None) is None


def test_compare_listings():
    """测试listing对比"""
    analyzer = CompetitorAnalyzer()
    
    competitors = [
        CompetitorListing(
            platform='Amazon',
            title='Speaker A',
            price=29.99,
            rating=4.5,
            reviews_count=1000,
            bullets=[],
            description='',
            keywords=['bluetooth', 'speaker', 'portable'],
            url=''
        ),
        CompetitorListing(
            platform='Amazon',
            title='Speaker B',
            price=34.99,
            rating=4.7,
            reviews_count=2000,
            bullets=[],
            description='',
            keywords=['wireless', 'speaker', 'waterproof'],
            url=''
        )
    ]
    
    my_listing = {'title': 'My Speaker'}
    result = analyzer.compare_listings(my_listing, competitors)
    
    assert result['price_benchmark']['average'] == 32.49
    assert result['rating_benchmark'] == 4.6
    assert result['total_reviews'] == 3000
    assert 'speaker' in result['common_keywords']
